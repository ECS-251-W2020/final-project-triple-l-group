# Account Wise Ledger: A New Design of Decentralized System
Yi-Chen Liu, Che-Yu Liu, Jia-Wei Liang © 2020 Copyright held by the owner/author(s).

---
## Introduction
Account-Wise Ledger is a new decentralized blockchain system with a lower storage burden and higher security. The two main designs of the system are Account-Wise Ledger and Three-End Commitment.
* **Account-Wise Ledger**  is a new type of blockchain data structure. Different from the original approach of the blockchain which mixes everyone’s transaction data and information together into a single chain and requires all participants to store a full copy of the data on that chain in order to join the network, we categorize every transaction by account. Each account is a single ledger book that cannot be sliced into multiple pieces but should contain every transaction respected to the account only, which can be considered as an atom-like unit.
* **Three-End Commitment** is a new consensus protocol that increases the security in the designed system, we remove the competition reward which is gained from the block creation. The following steps summarize this approach: (1) The sender announces the transaction task to each sub-network and the receiver; (2) The receiver announces the acknowledgment of each sub-network. The message includes the task information that is sent from the sender and receiver’s signature to prove that the task is accepted and verified by the receiver; (3) Each sub-network randomly selects one node as the representative operator; (4) Representative operators create the block by solving Proof-of-Work, then broadcast to each node in the whole network; (5) The operators who create the majority answer share the reward.

## Algorithm Design
The algorithm can be discussed into two parts: Account-Wise Ledger and Three-End commitment. Here elaborated detail steps of the algorithm has been implemented.
### Account-Wise Ledger
Account-Wise Ledger is a data structure that contains everyone's information into an atom-like structure. For each ledger, it would contain the user's ID, user's address, user's current transaction balance, and the whole transaction history stored in a blockchain. In order to implement this concept by actual programming code, we create Account-Wise Ledger as a class which has the following structure:
```
class AccountWiseLedger
    public:
        method constructor
        method setTransaction
        method createNewBlock
        method receiveResult
        method viewOwnerID
        method viewSubNetwork
        method viewPowDifficulty
        method viewActualBalance
        method viewPendingBalance
        method viewPlanningBalance
        method viewTransactionTask
        method viewTransactionTaskHandler
        method viewLastBlock
        method viewBlockchain
        method outputDict
        method outputJsonBytes
    private:
        variable ownerID
        variable subNetwork
        variable powDifficulty
        variable transactionBalance
        variable transactionTask
        variable transactionTaskHandler
        variable blockchain
```
### Three-End Commitment
Three-End Commitment is an actual communication protocol. We listed down the steps that a single communication would take as follow:
1. The sender announces the departure-task to everyone in the network and the receiver.
1. The sender's side transaction-block-creating procedure start:
    1. The receiver announces the acknowledgment to everyone. The message includes the task information that is sent from the sender and receiver's signature to prove that the task is accepted and verified by the receiver.
    1. Each sub-network randomly elect one node as the representative operator
    1. Every representative operator from each sub-network will create the block by solving Proof-of-Work, then broadcast to everyone in the whole network.
    1. Everyone starts to verify each block that it received, calculating the majority of the correct answer. The majority of the operators who create the correct answer would share the reward.
1. The sender announces the destination-task to everyone in the network and the receiver.
1. The receiver's side transaction-block-creating procedure start:
    1. The receiver announces the acknowledgment to everyone. The message includes the task information that is sent from the sender and receiver's signature to prove that the task is accepted and verified by the receiver.
    1. Each sub-network randomly elect one node as the representative operator
    1. Every representative operator from each sub-network will create the block by solving Proof-of-Work, then broadcast to everyone in the whole network.
    1. Everyone starts to verify each block that it received, calculating the majority of the correct answer. The majority of the operators who create the correct answer would share the reward.

## Code Design
The system needs to build up a DNS for any new peer to connect to the cloud. After acquiring a DNS table from the DNS, new users can connect to the cloud directly without any intermediate routers. The communication package should be well-defined. The data structure of each package is described as below.
### DNS Table
Once any node trying to establish a new connection with the DNS, the DNS will send back the DNS table, which is a `JSON` format.
```
DNSTable {
    "all": {
        memberID_1: [memberID_1_IP, memberID_1_PORT]
        memberID_2: [memberID_2_IP, memberID_2_PORT]
        ...
    }
    "subNetworkToIndex" {
        sebNetWorkID_1 (str): {
            memberID_1_1_Index: memberID_1_1 
            memberID_1_2_Index: memberID_1_2 
            memberID_1_3_Index: memberID_1_3
            ...
        }
        sebNetworkID_2 (str): {
            memberID_2_1_Index: memberID_2_1 
            memberID_2_2_Index: memberID_2_2 
            memberID_2_3_Index: memberID_2_3
            ...
        }
        ...
    }
    "subNetworkToNode" {
        sebNetworkID_1 (str): {
            memberID_1_1: memberID_1_1_Index
            memberID_1_2: memberID_1_2_Index 
            memberID_1_3: memberID_1_3_Index
            ...
        }
        sebNetworkID_2 (str): {
            memberID_2_1: memberID_2_1_Index 
            memberID_2_2: memberID_2_2_Index 
            memberID_2_3: memberID_2_3_Index
            ...
        }
        ...
    }
    "nodeToSubNetwork" {
        memberID_1_1: sebNetworkID_1 (int)
        memberID_2_1: sebNetworkID_2 (int)
        ...
    }
    "sizeOfSubNetwork" {
        sebNetworkID_1: len(sebNetworkID_1)
        sebNetworkID_2: len(sebNetworkID_2)
        ...
    }
}
```
### Client Instruction Package
Client Instruction Packages is a network package with a `JSON` format sent from each peer. The purpose of the usage of these packages is allowing peers to communicate with each other. Any peer can use the information contained in packages to proceed with corresponding reactions. Each package contains the following information:
* `type` describes action types.
    * `New Peer ACK` is sent from the sub-network where a new peer just joined. 
    * `DNS update` is sent from the DNS to inform a new updated DNS table.
    * `Request AWL List Update` is sent from a peer who wants to acquire the latest Account-Wise Ledger List.
    * `Send AWL List` is sent from a peer who has been asked to provide its Account-Wise Ledger List.
    * `Request Last Block Hash` is sent from a peer who wants to acquire the latest Last Block Hash of a certain peer.
    * `Send Last Block Hash` is sent from a peer who has been asked to provide its Last Block Hash.
    * `Request Receiver ACK` is sent from the transaction sender who wants to gain the confirmation of the task from the receiver.
    * `Send Receiver ACK` is sent from the transaction receiver. The receiver will sign the transaction if the task is acceptable from its perspective.
    * `New Transaction` is sent from a peer who wants to establish a new transaction
    * `Check Valid Transaction` is sent from the operators who want to check the validity of a certain transaction
    * `Ans Valid Transaction` is sent from peers who owned the sender's Account-Wise Ledger. Those peers will check the transaction sender's balance to determine whether the sender can afford the transaction amount or not.
    * `New Block` is sent from the operators who finished calculating Proof-of-Work.
* `data` contains the main body of the Client Instruction Package
* `senderID` contains the ID of the package sender
* `memo` contains the extra information. Optional.
* `target` only be used when a package sender wants to issue a `Check Valid Transaction` package. The `target` denoted a peer ID that the package sender wants to verify.

## Installation and Execution
In order to execute the whole system, a user need to establish the DNS first then create clients to create the cloud. Here described the details.
1. Download `AccountWiseLedger.py`, `AccountWiseLedgerDNS.py`, `Blockchain.py`, and `Main.py` into a local directory. All of these four documents should be placed in the same directory.
1. Open a terminal, change your current position to the directory where you put the above four documents.
1. In the terminal, type in `python AccountWiseLedgerDNS.py` to establish the DNS.
1. In the DNS, input a number for how many sub-networks that you want to establish.
1. Open another terminal, change your current position to the directory where you put the above four documents. Type in `python Main.py`
1. In the pop-up dialog, type in the account ID that you wish to use and the IP/Port of your DNS
1. Once you getting into the main window, you can make transactions.

Note, there are some requirements for this program that you should pre-install/ set up in your computer:
1. The Python version should be `Python 3.7`
1. Make sure that you have installed the `PyQt5` module.

## Copyright
Permission to make digital or hard copies of part or all of this work for personal or classroom use is granted without fee provided. Copyrights for third-party components of this work must be honored. For all other uses, contact the owner/author(s).<br>
[![license](https://img.shields.io/github/license/DAVFoundation/captain-n3m0.svg?style=flat-square)](https://github.com/ECS-251-W2020/final-project-triple-l-group/blob/master/LICENSE)
