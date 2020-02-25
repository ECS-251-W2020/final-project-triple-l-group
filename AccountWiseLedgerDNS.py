import socket
import json


def main():
    dnsSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port = 8000

    K_numOfSubNetwork = 1
    DNSTable = {
        "all": {},
        "nodeToSubNetwork": {},
        "subNetworkToNode": {index: {} for index in range(K_numOfSubNetwork)},
        "sizeOfSubNetwork": {index: 0 for index in range(K_numOfSubNetwork)}
    }

    def getHostnameIP():
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return None

    try:
        dnsSocket.bind((getHostnameIP(), port))
        print("DNS is online, the IP/Port is [", getHostnameIP(), ":", port, "]")
    except:
        print("Error occurred. Server shutdown...")
        return

    while True:
        inputMsg, sourceAddress = dnsSocket.recvfrom(1024)
        inputMsg = json.loads(inputMsg.decode())
        newPeer = None

        print(sourceAddress, "a.k.a [", inputMsg["senderID"], "] is connected. Action Type [", inputMsg["type"], "]")
        if inputMsg["type"] == "New Peer":

            if inputMsg["senderID"] not in DNSTable["all"]:
                newPeer = inputMsg["senderID"]
                assignedSubNetworkIndex = min(DNSTable["sizeOfSubNetwork"].keys(), key=lambda x: DNSTable["sizeOfSubNetwork"][x])
                DNSTable["subNetworkToNode"][assignedSubNetworkIndex][inputMsg["senderID"]] = True
                DNSTable["nodeToSubNetwork"][inputMsg["senderID"]] = assignedSubNetworkIndex
                DNSTable["sizeOfSubNetwork"][assignedSubNetworkIndex] += 1
            DNSTable["all"][inputMsg["senderID"]] = sourceAddress

            outputMsg = {"type": "DNS update", "data": DNSTable, "newPeer": newPeer}

            for nodeAddr in DNSTable["all"].values():
                dnsSocket.sendto(json.dumps(outputMsg).encode(), nodeAddr)

        elif inputMsg["type"] == "Request DNS Update":
            DNSTable["all"][inputMsg["senderID"]] = sourceAddress
            outputMsg = {"type": "DNS update", "data": DNSTable, "newPeer": newPeer}

            dnsSocket.sendto(json.dumps(outputMsg).encode(), sourceAddress)


if __name__ == "__main__":
    main()
