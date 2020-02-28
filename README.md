#Account Wise Ledger: A New Design of Decentralized System
Final Project for ECS 251 Operating System in UC Davis 2020 Winter<br>
Team: Triple L Group. Teammate: Yi-Chen Liu, Che-Yu Liu , Jia-Wei Liang
---
##Data Structure
The data structure of the system is listed and described as below sections.
###DNS Table

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