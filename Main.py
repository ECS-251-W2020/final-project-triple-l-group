from AccountWiseLedger import AccountWiseLedger
from urllib.parse import urlencode
from io import BytesIO
import pycurl
import json
import socket
import sys
import collections
import os
from distutils.util import strtobool
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, QMutex
from pprint import pprint


class ListenThread(QThread):
    listenedMsg = pyqtSignal(dict)

    def __init__(self, socket):
        super(ListenThread, self).__init__()
        self.__mutex = QMutex()
        self.__socket = socket

    def run(self):
        while True:
            self.__mutex.lock()
            inputMsg, sourceAddress = self.__socket.recvfrom(1024)
            inputMsg = json.loads(inputMsg)
            print("\t<LISTEN SOCKET SIDE>: ", inputMsg)
            self.__mutex.unlock()

            self.listenedMsg.emit(inputMsg)


class UserInterface(QtWidgets.QMainWindow, QThread):

    def __init__(self):
        super(UserInterface, self).__init__()
        self.__windowStartPositionX = 150
        self.__windowStartPositionY = 100
        self.__windowHeight = 600
        self.__windowWidth = 1000
        self.__programTitle = "User Interface"

        self.__accountID = input("User Name: ")
        self.__accountSubNetwork = ""
        self.__accountWiseLedgerDNS = ("192.168.0.29", 8000)
        self.__nodeList = {}
        self.__accountWiseLedgerList = {}
        self.__vote = collections.Counter()

        # Initialize the socket
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.bind((self.__getHostnameIP(), 5000))

        # Get Latest IP list from the DNS
        self.__initData()
        #self.__send({"type": "New Peer", "senderID": self.__accountID}, self.__accountWiseLedgerDNS)

        # Multi-Threading for Listening
        self.__mutex = QMutex()
        self.__listenThread = ListenThread(self.__socket)
        self.__listenThread.listenedMsg.connect(self.__updateLocal)
        self.__listenThread.start()

        # Create Main Frame
        self.__centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(self.__centralWidget)
        self.setGeometry(self.__windowStartPositionX, self.__windowStartPositionY, self.__windowWidth, self.__windowHeight)
        self.setWindowTitle(self.__programTitle)

        # Create Article Frame
        self.__messageFrame = QtWidgets.QTextBrowser(self)

        self.__awlUpdateButton = QtWidgets.QPushButton("Update Account Wise Ledger List", self)
        self.__awlUpdateButton.clicked.connect(self.awlUpdateButtonHandler)
        self.__dnsUpdateButton = QtWidgets.QPushButton("Update Peer List", self)
        self.__dnsUpdateButton.clicked.connect(self.dnsUpdateButtonHandler)

        # Manage the layout
        mainLayout = QtWidgets.QGridLayout()
        mainLayout.addWidget(self.__messageFrame, 0, 0, 1, 2)
        mainLayout.addWidget(self.__dnsUpdateButton, 1, 0, 1, 1)
        mainLayout.addWidget(self.__awlUpdateButton, 1, 1, 1, 1)

        self.__centralWidget.setLayout(mainLayout)
        self.show()

        # Create Main Frame
        # first join the network, initialization
        # create new AccountWiseLedger class for me
        # retrieve others AccountWiseLedgers from the network
        # retrieve the address table for every member in the network

    def __initData(self):
        self.__send({"type": "New Peer", "senderID": self.__accountID}, self.__accountWiseLedgerDNS)
        self.__nodeList = self.__listen()["data"]
        if len(self.__nodeList["subNetworkToNode"][str(self.__nodeList["nodeToSubNetwork"][self.__accountID])]) == 1:
            self.__accountWiseLedgerList[self.__accountID] = AccountWiseLedger(self.__accountID, self.__nodeList["nodeToSubNetwork"][self.__accountID])

        print("\n<----INITIALIZATION SYS---->\n")
        print("[VoteTable]: ", self.__vote)
        print("[All Node]:", self.__nodeList)
        print("[AWL List]: ", self.__accountWiseLedgerList)
        print("\n<-------------------------->\n")

    def __getHostnameIP(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return None

    def __send(self, outputMsg, ipPortTuple):
        self.__socket.sendto(json.dumps(outputMsg).encode(), ipPortTuple)
        return

    def __listen(self):
        inputMsg = None
        while not inputMsg:
            inputMsg, sourceAddress = self.__socket.recvfrom(1024)
            inputMsg = json.loads(inputMsg)

        return inputMsg

    def __updateLocal(self, inputMsg):

        if inputMsg["type"] == "TEST":
            print("Just a test msg")
        elif inputMsg["type"] == "DNS update":
            self.__nodeList = inputMsg["data"]

            if inputMsg["newPeer"] is not None:
                self.__accountWiseLedgerList[inputMsg["newPeer"]] = AccountWiseLedger(inputMsg["newPeer"], inputMsg["data"]["nodeToSubNetwork"][inputMsg["newPeer"]])
                self.__send({"type": "New Peer ACK", "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["newPeer"]]))

            print("\n<----Heard [DNS update]---->\n")
            print("[VoteTable]: ", self.__vote)
            print("[All Node]:", self.__nodeList)
            print("[AWL List]: ", self.__accountWiseLedgerList)
            print("\n<-------------------------->\n")

        elif inputMsg["type"] == "Request AccountWiseLedgerList Update":
            transferedAWLL = {}
            for key in self.__accountWiseLedgerList:
                transferedAWLL[key] = self.__accountWiseLedgerList[key].outputDict

            self.__send({"type": "Send AccountWiseLedgerList", "data": transferedAWLL, "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))

            print("\n<----Heard [Request AccountWiseLedgerList Update]---->\n")
            print("[VoteTable]: ", self.__vote)
            print("[All Node]:", self.__nodeList)
            print("[AWL List]: ", self.__accountWiseLedgerList)
            print("\n<-------------------------->\n")

        elif inputMsg["type"] == "Send AccountWiseLedgerList":
            self.__vote[json.dumps(inputMsg["data"]).encode()] += 1

            wonAWLL = max(self.__vote.keys(), key=lambda x: self.__vote[x])
            if self.__vote[wonAWLL] > (len(self.__nodeList["all"]) - 1) // 2:
                self.__accountWiseLedgerList = json.loads(wonAWLL)
                for key in self.__accountWiseLedgerList:
                    self.__accountWiseLedgerList[key] = AccountWiseLedger.createByJsonBytes(json.dumps(self.__accountWiseLedgerList[key]))
                self.__vote = collections.Counter()

            print("\n<----Heard [Send AccountWiseLedgerList]---->\n")
            print("[VoteTable]: ", self.__vote)
            print("[All Node]:", self.__nodeList["all"])
            print("[AWL List]: ", self.__accountWiseLedgerList)
            print("\n<-------------------------->\n")

    def dnsUpdateButtonHandler(self):
        outputMsg = {"type": "Request DNS Update", "senderID": self.__accountID}
        self.__send(outputMsg, self.__accountWiseLedgerDNS)

    def awlUpdateButtonHandler(self):
        for nodeID in self.__nodeList["subNetworkToNode"][str(self.__nodeList["nodeToSubNetwork"][self.__accountID])]:
            self.__send({"type": "Request AccountWiseLedgerList Update", "senderID": self.__accountID}, tuple(self.__nodeList["all"][nodeID]))

    def newTransaction(self, task):
        return self.__accountWiseLedgerList[self.__accountID].newTransaction(task)

    @staticmethod
    def getFromURL(url):
        b_obj = BytesIO()
        crl = pycurl.Curl()

        crl.setopt(crl.URL, url)
        crl.setopt(crl.WRITEDATA, b_obj)

        crl.perform()
        crl.close()

        get_body = b_obj.getvalue()
        return get_body.decode("utf8")

    @staticmethod
    def postToURL(url, msg):
        crl = pycurl.Curl()
        crl.setopt(crl.URL, url)

        crl.setopt(crl.POSTFIELDS, urlencode(msg))
        crl.perform()
        crl.close()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
