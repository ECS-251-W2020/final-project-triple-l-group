import socket
import json


def testMain():
    dnsSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    DNSTable = {}
    port = 8000

    def getHostnameIP():
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return None

    try:
        dnsSocket.bind((getHostnameIP(), port))
        print("DNS is online, the IP and Port is: ", getHostnameIP(), ":", port)
    except:
        print("Error occurred. Server shutdown...")
        return

    while True:
        inputMsg, sourceAddress = dnsSocket.recvfrom(1024)
        inputMsg = json.loads(inputMsg.decode())

        print(sourceAddress, " is connected. Action Type [", inputMsg["type"], "]")
        if inputMsg["type"] == "New Peer":
            DNSTable[inputMsg["data"]] = sourceAddress
            outputMsg = {"type": "DNS update", "data": DNSTable}

            for node in DNSTable.values():
                dnsSocket.sendto(json.dumps(outputMsg).encode(), node)

        elif inputMsg["type"] == "Request Update":
            DNSTable[inputMsg["data"]] = sourceAddress
            outputMsg = {"type": "DNS update", "data": DNSTable}

            dnsSocket.sendto(json.dumps(outputMsg).encode(), sourceAddress)


if __name__ == "__main__":
    testMain()
