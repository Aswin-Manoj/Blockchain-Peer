# Blockchain-Peer
Blockchain peer with UDP communication, consensus, and synchronization.

# General Discussion
Code should work properly by just running python3 peerA3.py. I have hardcoded my port number and also hardcoded the main peer and port. 
Constants like consensus interval, number of attempts for getting blocks, how long we have to wait after each getBlockRequest phase etc is on the top of the code. Feel free to change this value according to your requirements. The values set right now should be enough to do all the required processes. For consensus, if the provided attempts are not enough to get all the blocks, feel free to increase it. 

The code roughly takes around 2 to 4 minutes to synchronize if the first chain being synchronized is valid. Otherwise it will take approximately 2 minutes every chain until the valid chain has been met. Once synchronized, you will see , "Consensus Complete: New Chain is Valid". Also, the terminal will display a message saying which phase it is in (like stats, validation, getBlock etc). This will provide more clarity.  

For the nonce in block constraints (line 231), I am checking it so that the block is valid if nonce is max 40 characters

I implemented this program without any multithreading or select. I used a bunch of boolean variables to control what state I am in (like statsPhase, consensusPhase, validationPhase, getBlockPhase etc). Everything happens in one big while Loop


## Code How and Where

### Cleaning up Gossip messages

I am implementing a dictionary data structure to store gossip and gossip reply messages along with the time that I received them. From line 60 to 69 I handle gossip replies in handleGossipReply(data) function and from line 75 to 101 I handle gossip messages.  I have one main while loop (From line 301 till end) in my code that runs forever. Whenever I start a new iteration in this loop, the first thing I do is call the cleanupPeerList() on line 304. This function is located from line 106 to line 117. In this function , I first check what the timeDifference is and if its greater than 60 seconds, I remove it.

### Verify entire chain

After my getBlockPhase(From line 469 to 549) is over (I have got all the blocks), I begin Validation Phase(From line 554 to 577). This piece of code calls the function validateChain() (It is located from lines 201 to 210). This function basically contains a for loop that calls validateBlock() function (from 166 to 196) on each block that was collected from genesis till the top. In the validateBlock() function, first it checks if the block follows the constraints by calling validateBlockConstraints() function( from line 229 till 242). validateBlockConstraints() checks if nonce, number of messages and number of characters in each message are following the appropriate constraints. Now after this is done, in the validateBlock(), I follow the steps given by the professor in A3 instructions to calculate the hash and then confirm if the hashes match. In this way I validate each block and hence verify my whole chain.

### Choose longest chain

I do multiple steps to achieve this. First I collect all the stat replies when I enter the statsPhase (From line 435 till 465). I call handleStatsReply() (From line 124 till 139) and add the replies to list. I store stat replies in a tuple, the first item in the tuple is the hash and height , and the second item is a list that contains all the peers that share that height and hash. Then I call the function sortStatsReplies() (from line 144 till 146) to sort the stat replies first on their height and then if two heights are same , on the number of peers all in descending order. After this, I move onto the getBlockPhase (line 469 till 549) where I start requesting blocks from the first item in the sortedStatReplies list which will be the longest chain since its descending order. And hence I choose the longest chain.
