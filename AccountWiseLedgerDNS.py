import threading
import socket
import json
import os
from pprint import pprint


class AccountWiseLedgerDNS(object):
    
    def __init__(self, K):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__ip = self.__getHostnameIP()
        self.__port = 8000
        self.__socketBufferSize = 64 * 1024 * 1024

        self.__K_numOfSubNetwork = K
        self.__DNSTable = {}
        self.__resetDNSTable()

        try:
            self.__socket.bind((self.__ip, self.__port))
            print("DNS is online, the IP/Port is [", self.__ip, ":", self.__port, "]. Type in \"man\" to browse available commands")
        except:
            print("Error occurred. Server shutdown...")
            return

    def __resetDNSTable(self):
        self.__DNSTable = {
            "all": {},
            "nodeToSubNetwork": {},
            "subNetworkToNode": {networkIndex: {} for networkIndex in range(self.__K_numOfSubNetwork)},
            "subNetworkToIndex": {networkIndex: {} for networkIndex in range(self.__K_numOfSubNetwork)},
            "sizeOfSubNetwork": {networkIndex: 0 for networkIndex in range(self.__K_numOfSubNetwork)}
        }

    def __getHostnameIP(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return None

    def listen(self):
        while True:
            inputMsg, sourceAddress = self.__socket.recvfrom(self.__socketBufferSize)
            inputMsg = json.loads(inputMsg.decode())
            newPeer = None

            if inputMsg["type"] == "exit":
                break
            else:
                print(sourceAddress, "a.k.a [", inputMsg["senderID"], "] is connected. Action Type [", inputMsg["type"], "]\n" + "[" + socket.gethostname().strip() + " @ " + self.__ip + ":" + str(self.__port) + "] $ ", end="")
                if inputMsg["type"] == "New Peer":

                    if inputMsg["senderID"] not in self.__DNSTable["all"]:
                        newPeer = inputMsg["senderID"]
                        assignedSubNetworkIndex = min(self.__DNSTable["sizeOfSubNetwork"].keys(), key=lambda x: self.__DNSTable["sizeOfSubNetwork"][x])
                        self.__DNSTable["subNetworkToNode"][assignedSubNetworkIndex][inputMsg["senderID"]] = len(self.__DNSTable["subNetworkToNode"][assignedSubNetworkIndex])
                        self.__DNSTable["subNetworkToIndex"][assignedSubNetworkIndex][str(len(self.__DNSTable["subNetworkToIndex"][assignedSubNetworkIndex]))] = inputMsg["senderID"]
                        self.__DNSTable["nodeToSubNetwork"][inputMsg["senderID"]] = assignedSubNetworkIndex
                        self.__DNSTable["sizeOfSubNetwork"][assignedSubNetworkIndex] += 1
                    self.__DNSTable["all"][inputMsg["senderID"]] = sourceAddress

                    outputMsg = {"type": "DNS update", "data": self.__DNSTable, "newPeer": newPeer}

                    for nodeAddr in self.__DNSTable["all"].values():
                        self.__socket.sendto(json.dumps(outputMsg).encode(), nodeAddr)

                elif inputMsg["type"] == "Request DNS Update":
                    self.__DNSTable["all"][inputMsg["senderID"]] = sourceAddress
                    outputMsg = {"type": "DNS update", "data": self.__DNSTable, "newPeer": newPeer}

                    self.__socket.sendto(json.dumps(outputMsg).encode(), sourceAddress)

    def send(self):
        while True:
            print("[" + socket.gethostname().strip() + " @ " + self.__ip + ":" + str(self.__port) + "] $ ", end="")
            inputMsg = input()
            if inputMsg == "exit":
                self.__socket.sendto(json.dumps({"type": "exit"}).encode(), (self.__ip, self.__port))
                break
            elif inputMsg == "ls":
                pprint(self.__DNSTable)
            elif inputMsg == "re":
                self.__resetDNSTable()
                print("DNS table is cleaned up.")
            elif inputMsg == "cls":
                os.system("cls")
            elif inputMsg == "ipconfig":
                print("Current Local Administrator: ", socket.gethostname())
                print("IP Address: ", self.__ip)
                print("Port Number: ", self.__port)
                print("Socket Buffer Size: ", self.__socketBufferSize)
                print("Designated number of Sub-Networks: ", self.__K_numOfSubNetwork)
            elif inputMsg == "man":
                manual = {
                    "ls": "List down the current DNS table",
                    "re": "Clean up the DNS table",
                    "cls": "Clean up the console out",
                    "ipconfig": "Show all network settings",
                    "man": "Show all available commands",
                    "exit": "Shutdown the DNS"
                }

                print("The following commands are available:")
                for index, item in enumerate(manual):
                    print(index, ". ", item, "\t", manual[item])
            else:
                print("Unknown command.")


def main():
    K_numOfSubNetwork = int(input("The number of Sub-Network K (default = 1): ") or 1)
    myDNS = AccountWiseLedgerDNS(K_numOfSubNetwork)
    
    threadListen = threading.Thread(target=myDNS.listen, args=())
    threadSend = threading.Thread(target=myDNS.send, args=())

    threadListen.start()
    threadSend.start()


if __name__ == "__main__":
    main()
