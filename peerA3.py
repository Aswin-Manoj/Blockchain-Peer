#peerA3.py

import socket
import uuid
import time
import json
import random
import hashlib

peerList = {}
peerIDs = {}
statReplies = {}
sortedStatReplies = []
getBlockReplies = []
validChain = []
announceQueue = []

DIFFICULTY = 8
CONSENSUS_INTERVAL = 120
STAT_REPLY_INTERVAL = 5
FIRST_GOSSIP_INTERVAL = 8
GOSSIP_INTERVAL = 30
GET_BLOCK_INTERVAL = 10
GET_BLOCK_ATTEMPTS = 30

myHost = ""
myPort = 8730

mainPeer = "silicon.cs.umanitoba.ca"
mainPort = 8999

#
#Send Gossip messages to 3 random peers (Will also forward recievied gossip messages)
#
def intiateGossip(sock:socket, data):

    if(data == ""):
        print("Sending Gossip Message")
        newID = str(uuid.uuid4())

        gossipMessage = {
        "type": "GOSSIP",
        "host": myHost,
        "port": myPort,
        "id": newID,
        "name": "NovaCore"
        }
    else: #If Data is non empty, that means I am going to forward this gossip message
        gossipMessage = data

    peersToSend = random.sample(list(peerList.items()), min(3,len(peerList)))
    msg = json.dumps(gossipMessage)

    for(host, port), peerInfo in peersToSend:
        sock.sendto(msg.encode(), (host, port))

#
#Adds gossip replies to a peerList 
#
def handleGossipReply(data):
    host = data["host"]
    port = data["port"]
    
    key = (host,port)
    peerInfo = {
    "recvTime": time.time()
    }

    peerList[key] = peerInfo


#
#Deal with recieved gossip messages by adding them to peerList
#
def handleGossip(sock:socket , data):

    host = data["host"]
    port = data["port"]

    if data["id"] not in peerIDs and not(host == myHost and port == myPort ):
  
        key = (host,port)
        peerInfo = {
        "recvTime": time.time()
        }

        peerList[key] = peerInfo
        
        peerIDs[data["id"]] = data["id"]

        gossipReplyMessage = {
        "type": "GOSSIP_REPLY",
        "host": myHost,
        "port": myPort,
        "name": "NovaCore"
        }

        msg = json.dumps(gossipReplyMessage)
        sock.sendto(msg.encode(), (host, port))

        intiateGossip(sock, data)

#
#Cleanup peerList if peers have timed out
#
def cleanupPeerList():

    currentTime = time.time()

    for(host, port), peerInfo in list(peerList.items()):
        recvTime = peerInfo["recvTime"]
        timeDifference = currentTime - recvTime
         
        #If more than 1 minute, kick peer
        if(timeDifference > 60):
            print("Removing peer "+host+":"+str(port)+" due to Inactivity")
            del peerList[(host,port)]
        


#
#Handle stats reply 
#
def handleStatsReply(data, addr):
    
    height = data["height"]
    hash = data["hash"]
    
    if(len(validChain) > 0): #Ignore all chains that have lower height than your current chain
        if(isinstance(height, int) and height <= len(validChain)):
            return

    if isinstance(height, int) and hash[-1*DIFFICULTY:]=='0'*DIFFICULTY:

        key = (height, hash)
        if key not in statReplies:
            statReplies[key] = []    

        statReplies[key].append(addr)

#
#Sort recieved stat replies
#
def sortStatsReplies():
    global sortedStatReplies
    sortedStatReplies = sorted(statReplies.items(), key = lambda x: (x[0][0] , len(x[1])) , reverse= True )
    


def sendStatsMessage(sock:socket):
    
    print("Sending Stats Message to available peers")

    statsMessage = {
    "type":"STATS"
    }
    
    msg = json.dumps(statsMessage)

    for(host, port), peerInfo in list(peerList.items()):
        sock.sendto(msg.encode(), (host, port))
        
#
#Validates a block 
#
def validateBlock(newBlock, blockList):

    if not validateBlockConstraints(newBlock):
        return False

    hashBase = hashlib.sha256()
    blockHeight = newBlock["height"]

    if blockHeight != 0: #Skip if genesis block
        lastHash = blockList[blockHeight-1]["hash"]
        hashBase.update(lastHash.encode())
    
    hashBase.update(newBlock["minedBy"].encode())
    
    for m in newBlock["messages"]:
        hashBase.update(m.encode())

    hashBase.update(newBlock["timestamp"].to_bytes(8, 'big'))

    hashBase.update(newBlock["nonce"].encode())

    hash = hashBase.hexdigest()

    if hash[-1 * DIFFICULTY:] != '0' * DIFFICULTY:
        print("Block was not difficult enough: {}".format(hash))
        return False

    if( hash == newBlock["hash"]):
        return True
    else:
        return False

#   
#Validates a block chain by iterating through and using validateBlock() 
#
def validateChain(blockList):
    
    for i in range(len(blockList)):

        currentBlock = blockList[i]
        if not validateBlock(currentBlock, blockList):
            return False

    
    return True

#
#Adds all the queued mined blocks to my chain (After consensus)
#
def handleAnnounceQueue():
    for msg in announceQueue:
        announceHeight = msg["height"]
        if(len(validChain) == announceHeight):
            if(validateBlock(msg , validChain)):
                print("Adding Mined Block:")
                print(msg)
                print("")
                msg["type"] = "GET_BLOCK_REPLY"
                validChain.append(msg)

#
#Check if a block is following all the required constraints
#
def validateBlockConstraints(blockMsg):

    if len(blockMsg["nonce"]) > 40:
        return False
    
    if len(blockMsg["messages"]) > 10 or len(blockMsg["messages"]) < 1:
        return False


    for message in blockMsg["messages"]:
        if len(message) > 20:
            return False
        
    return True







if __name__ == "__main__":
  

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('',myPort))
    sock.settimeout(0.1)

    hostname = socket.gethostname()
    myHost = socket.gethostbyname(hostname)

    newID = str(uuid.uuid4())
    gossipMessage = {
    "type": "GOSSIP",
    "host": myHost,
    "port": myPort,
    "id": newID,
    "name": "NovaCore"
    }
    
    print("Sending Gossip message to peer "+mainPeer+" on port "+str(mainPort))
    msg = json.dumps(gossipMessage)
    sock.sendto(msg.encode(), (mainPeer, mainPort))

    firstGossipPhase = True
    firstGossipTimer = time.time()

    consensusPhase = True
    consensusTimer = time.time()

    statsPhase = True
    sendStats = True
    
    recvStats = False
    recvStatsTimer = time.time()

    #GetBlockRequestsPhase
    getBlockPhase = False
    getBlockRequest = True
    recvBlocks = False
    recvBlockTimer = time.time()
    currentGroup = 0
    createArray = True
    attempt = 0



    validationPhase = False


    gossipTimer = time.time()

    while True:
        try:
            #Start every loop with checking if your peer list is up to date 
            cleanupPeerList()

            data, addr  = sock.recvfrom(2048)
            #print(data.decode())
            jsonMsg = json.loads(data)
            type = jsonMsg["type"]

            #Gossip  every 30 seconds
            if(time.time() - gossipTimer >=GOSSIP_INTERVAL):
                gossipTimer = time.time()
                intiateGossip(sock,"")

            if(type == "GOSSIP_REPLY"):

                handleGossipReply(jsonMsg)
                
            if(type == "GOSSIP"):
                
                handleGossip(sock,jsonMsg)

            if(type == "CONSENSUS"):
                if(not consensusPhase):
                    print("\n")
                    print("Consensus Request Received: Beginning Consenus")
                    consensusPhase = True
                    consensusTimer = time.time()

            if(type == "STATS"):
                if(len(validChain) > 0):
                    height = len(validChain)
                    hash = validChain[len(validChain) - 1]["hash"]

                    host = addr[0]
                    port = addr[1]
                    
                    statReplyMessage = {
                    "type": "STATS_REPLY",
                    "height": height,
                    "hash": hash
                    }

                    msg = json.dumps(statReplyMessage)
                    sock.sendto(msg.encode(), (host, port))
                    

            if(type == "GET_BLOCK"):
                if(len(validChain) > 0):
                    height = jsonMsg["height"]
                    host = addr[0]
                    port = addr[1]

                    getBlockReply = ""
                    if height >= len(validChain):

                        getBlockReply={
                        "type": "GET_BLOCK_REPLY",
                        "hash": None,
                        "height": None,
                        "messages": None,
                        "minedBy": None,
                        "nonce": None,
                        "timestamp": None
                        }

                    else:

                        getBlockReply = validChain[height]

                    msg = json.dumps(getBlockReply)
                    sock.sendto(msg.encode(), (host, port))


            if(type == "ANNOUNCE"):

                announceHeight = jsonMsg["height"]

                if(firstGossipPhase or consensusPhase):
                    announceQueue.append(jsonMsg)
                else:
                    if(len(validChain) == announceHeight):
                        if(validateBlock(jsonMsg , validChain)):
                            print("")
                            print("Adding Mined Block:")
                            print(jsonMsg)
                            print("")
                            jsonMsg["type"] = "GET_BLOCK_REPLY"
                            validChain.append(jsonMsg)

                    
            
            #Run this if loop only once during entire code 
            if(firstGossipPhase and time.time() - firstGossipTimer > FIRST_GOSSIP_INTERVAL):
                if(peerList):
                    firstGossipPhase = False
                    print("\n")
                    print("Beginning Consensus")
                else:
                    print("Did not receive gossip reply from well known peer, resending gossip now")
                    hostname = socket.gethostname()
                    myHost = socket.gethostbyname(hostname)

                    newID = str(uuid.uuid4())
                    gossipMessage = {
                    "type": "GOSSIP",
                    "host": myHost,
                    "port": myPort,
                    "id": newID,
                    "name": "NovaCore"
                    }
                    
                    print("Sending Gossip message to peer "+mainPeer+" on port "+str(mainPort))
                    msg = json.dumps(gossipMessage)
                    sock.sendto(msg.encode(), (mainPeer, mainPort))
                    firstGossipTimer = time.time()


            #Do consensus every 2 minutes
            if(time.time() - consensusTimer > CONSENSUS_INTERVAL):
                if(not consensusPhase):
                    print("\n")
                    print("Beginning Consensus")
                    consensusPhase = True
                    consensusTimer = time.time() #Reset consensus timer
            
##################################----------CONSENSUS MAIN CODE STARTS---------#####################################
            if(not firstGossipPhase):
                #Basically if you are not in the first gossipPhase, you are allowed to start with consensus
                if(consensusPhase): 

###################################---------STATS PHASE---------###################################################

                    #Begin stat phase
                    if(statsPhase):
                             
                        if(recvStats):
                            
                            if(type == "STATS_REPLY"):
                                handleStatsReply(jsonMsg, addr) #Add all the replies to a seperate list

                            if (time.time() - recvStatsTimer > STAT_REPLY_INTERVAL):
                                #Stats Phase has ended, move onto getBlock Phase
                                recvStats = False
                                statsPhase = False
                                getBlockPhase = True
                                sortStatsReplies()
                                print("Received Stat Replies")
                                for peer in sortedStatReplies:
                                    print(peer)
                                print("Begin getBlock Phase")
                                
                            
                        #send stats message to all available peers
                        if(sendStats):                                   
                            sendStatsMessage(sock)   
                            recvStatsTimer = time.time()
                            sendStats = False
                            recvStats = True
                            print("Begin Receiving statsReplies")                            

                        #Setting this back to True for next consensus 
                        if(not statsPhase):
                            sendStats = True
                        
######################################------------GET BLOCK PHASE-------------############################################
                    
                    if(getBlockPhase):
                        
                        #My Chain is either the longest or I have run out of peer groups
                        if(currentGroup == len(sortedStatReplies)):
                            #End Consensus
                            if(len(sortedStatReplies) == 0):
                                print("\n")
                                print("Consensus Done")  
                                print("\n")
                            else:
                                print("No Groups Replied All the Blocks: Ending Consensus For Now")
                            statReplies = {}
                            sortedStatReplies = {}
                            consensusPhase = False
                            statsPhase = True #for next consensus
                            currentGroup = 0
                            consensusTimer= time.time()
                            getBlockPhase = False
                            getBlockRequest = False
                            handleAnnounceQueue()

                        #ReceiveBlocks after seNding getblock requests
                        if(recvBlocks):
                            if(type == "GET_BLOCK_REPLY"):
                                replyHeight = jsonMsg["height"]
                                replyHash = jsonMsg["hash"]
                                if(isinstance(replyHeight, int) and replyHeight < len(getBlockReplies) and validateBlockConstraints(jsonMsg) and replyHash[-1*DIFFICULTY:]=='0'*DIFFICULTY):                             
                                    getBlockReplies[replyHeight] = jsonMsg
                               
                            if(time.time() - recvBlockTimer > GET_BLOCK_INTERVAL):

                                if None in getBlockReplies:
                                    blocksReceived = len([x for x in getBlockReplies if x is not None])
                                    print("Blocks Received : "+str(blocksReceived)+ "/"+ str(len(getBlockReplies)))
                                    recvBlocks = False
                                    getBlockRequest = True
                                else:
                                    print("Begin validation Phase")
                                    recvBlocks = False
                                    getBlockPhase = False
                                    validationPhase = True
                                    attempt = 0
                                    createArray = True
                                
                        #Send getBlock request to peers in a specific group 
                        if(getBlockRequest): 
                            attempt = attempt + 1  
                            print("Send get block request : attempt "+str(attempt)+" for group "+str(currentGroup))
                            pList = sortedStatReplies[currentGroup][1]
                            height = sortedStatReplies[currentGroup][0][0]

                            if(createArray): 
                                getBlockReplies = [None] * (height)
                                createArray = False
                            
                            for i in range(height):
                                #Load balance get block requests
                                randomPeer = random.choice(list(pList))
                                host , port = randomPeer
                                getBlockMessage={
                                "type": "GET_BLOCK",
                                "height": i
                                }
                                if getBlockReplies[i] is None:
                                    msg = json.dumps(getBlockMessage)
                                    sock.sendto(msg.encode(), (host, port))

                            recvBlockTimer = time.time()
                            getBlockRequest = False
                            recvBlocks = True
                            print("Begin receiving get block requests")

                        if(attempt == GET_BLOCK_ATTEMPTS):
                            print("Did not get all blocks from current group of peers. Moving onto next group")
                            createArray = True
                            currentGroup = currentGroup + 1
                            attempt = 0

                        #Set this to true for next getBlockPhase
                        if(not getBlockPhase):
                            getBlockRequest = True

#######################################------------VALIDATION PHASE------------##########################################


                    if(validationPhase):

                        if validateChain(getBlockReplies):
                            print("\n")
                            print("Consensus Complete: New Chain is Valid")
                            print("\n")
                            validChain = getBlockReplies
                            statReplies = {}
                            sortedStatReplies = {}
                            consensusPhase = False
                            validationPhase = False
                            statsPhase = True #for next consensus
                            currentGroup = 0
                            consensusTimer= time.time()
                            handleAnnounceQueue()

                            #print(getBlockReplies)
                        else:
                            print("Invalid Chain: Begin process for next group")
                            print("\n")

                            currentGroup = currentGroup + 1
                            validationPhase = False
                            getBlockPhase = True
                        


        except socket.timeout:
            continue
        except json.JSONDecodeError:
            print("Got a reply, but it was not json")
        except Exception as e:
            continue
