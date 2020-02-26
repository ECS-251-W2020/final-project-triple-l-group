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
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QThread, pyqtSignal, QMutex
from pprint import pprint


class ListenThread(QThread):
    listenedMsg = pyqtSignal(dict)

    def __init__(self, socket):
        super(ListenThread, self).__init__()
        self.__mutex = QMutex()
        self.__socket = socket
        self.__socketBufferSize = 1024

    def run(self):
        while True:
            self.__mutex.lock()
            inputMsg, sourceAddress = self.__socket.recvfrom(self.__socketBufferSize)
            inputMsg = json.loads(inputMsg)
            print("\t<LISTEN SOCKET SIDE>: ", inputMsg)
            self.__mutex.unlock()

            self.listenedMsg.emit(inputMsg)


class UserInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super(UserInterface, self).__init__()
        self.__windowStartPositionX = 150
        self.__windowStartPositionY = 100
        self.__windowHeight = 600
        self.__windowWidth = 1000
        self.__programTitle = "Account Wise Ledger User Interface"

        self.__accountID = self.getInputFromPopUpDialog("Your User Name:")
        self.__accountSubNetwork = ""
        self.__accountWiseLedgerDNS = ("168.150.6.83", 8000)
        self.__nodeList = {}
        self.__accountWiseLedgerList = {}
        self.__vote = collections.Counter()

        # Initialize the socket
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.bind((self.__getHostnameIP(), 0))

        # Initialize data
        self.__initData()

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

        # Create Transactions input Field and Current Balance
        self.__userInfoLabel = QtWidgets.QLabel(self)
        self.__userInfoLabel.setText("User: " + self.__accountID)
        self.__balanceLine = QtWidgets.QLineEdit()
        self.__transactionLineReceiverID = QtWidgets.QLineEdit()
        self.__transactionLineAmount = QtWidgets.QLineEdit()
        self.__makeTransactionButton = QtWidgets.QPushButton("Make Transaction", self)
        self.__makeTransactionButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.__makeTransactionButton.clicked.connect(self.newTransactionButtonHandler)

        # Create Peers Table
        self.__peersTable = QtWidgets.QTextBrowser(self)

        # Create Log Frame
        self.__logFrame = QtWidgets.QTextBrowser(self)

        # Create Buttons
        self.__awlUpdateButton = QtWidgets.QPushButton("Update AWL List", self)
        self.__awlUpdateButton.clicked.connect(self.awlUpdateButtonHandler)
        self.__dnsUpdateButton = QtWidgets.QPushButton("Update Peer List", self)
        self.__dnsUpdateButton.clicked.connect(self.dnsUpdateButtonHandler)

        # Create Progress Bar
        self.__progressBar = QtWidgets.QProgressBar(self)

        # Manage the layout
        mainLayout = QtWidgets.QGridLayout()
        mainLayout.addWidget(self.__peersTable, 0, 0, 5, 2)
        mainLayout.addWidget(self.__userInfoLabel, 0, 2, 1, 2)
        mainLayout.addWidget(self.__balanceLine, 1, 2, 1, 1)
        mainLayout.addWidget(self.__transactionLineReceiverID, 2, 2, 1, 1)
        mainLayout.addWidget(self.__transactionLineAmount, 3, 2, 1, 1)
        mainLayout.addWidget(self.__makeTransactionButton, 1, 3, 3, 1)
        mainLayout.addWidget(self.__logFrame, 4, 2, 1, 2)
        mainLayout.addWidget(self.__dnsUpdateButton, 5, 0, 1, 1)
        mainLayout.addWidget(self.__awlUpdateButton, 5, 1, 1, 1)
        mainLayout.addWidget(self.__progressBar, 5, 2, 1, 2)

        self.__centralWidget.setLayout(mainLayout)
        self.show()

    def __initData(self):
        self.__send({"type": "New Peer", "senderID": self.__accountID}, self.__accountWiseLedgerDNS)
        self.__nodeList = self.__listen()["data"]
        self.__accountSubNetwork = str(self.__nodeList["nodeToSubNetwork"][self.__accountID])
        if len(self.__nodeList["subNetworkToNode"][self.__accountSubNetwork]) == 1:
            self.__accountWiseLedgerList[self.__accountID] = AccountWiseLedger(self.__accountID, self.__nodeList["nodeToSubNetwork"][self.__accountID])
        else:
            self.awlUpdateButtonHandler()

        self.printLog("INITIALIZATION SYS", "console")

    def __getHostnameIP(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return None

    def __listen(self):
        inputMsg = None
        while not inputMsg:
            inputMsg, sourceAddress = self.__socket.recvfrom(1024)
            inputMsg = json.loads(inputMsg)

        return inputMsg

    def __send(self, outputMsg, ipPortTuple):
        self.__socket.sendto(json.dumps(outputMsg).encode(), ipPortTuple)
        return

    def __broadcast(self, outputMsg, targetSubNetworkSet=None):
        if targetSubNetworkSet is None:
            for nodeID in self.__nodeList["all"].keys():
                if nodeID != self.__accountID:
                    self.__send(outputMsg, tuple(self.__nodeList["all"][nodeID]))
        else:
            for nodeID in self.__nodeList["all"].keys():
                if str(self.__nodeList["nodeToSubNetwork"][nodeID]) in targetSubNetworkSet and nodeID != self.__accountID:
                    self.__send(outputMsg, tuple(self.__nodeList["all"][nodeID]))

    def __updateLocal(self, inputMsg):

        if inputMsg["type"] == "TEST":
            print("Just a test msg")

        elif inputMsg["type"] == "DNS update":
            self.__nodeList = inputMsg["data"]
            if inputMsg["newPeer"] is not None:
                self.__accountWiseLedgerList[inputMsg["newPeer"]] = AccountWiseLedger(inputMsg["newPeer"], inputMsg["data"]["nodeToSubNetwork"][inputMsg["newPeer"]])
                self.__send({"type": "New Peer ACK", "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["newPeer"]]))

            self.printLog("Heard [DNS update]")

        elif inputMsg["type"] == "Request AccountWiseLedgerList Update":
            transferedAWLL = {key: self.__accountWiseLedgerList[key].outputDict for key in self.__accountWiseLedgerList}
            self.__send({"type": "Send AccountWiseLedgerList", "data": transferedAWLL, "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))

            self.printLog("Heard [Request AccountWiseLedgerList Update]")

        elif inputMsg["type"] == "Send AccountWiseLedgerList":
            self.__vote[json.dumps(inputMsg["data"]).encode()] += 1

            wonAWLL = max(self.__vote.keys(), key=lambda x: (self.__vote[x], len(x)))
            if self.__vote[wonAWLL] > (len(self.__nodeList["all"]) - 1) // 2:
                self.__accountWiseLedgerList = json.loads(wonAWLL)
                for key in self.__accountWiseLedgerList:
                    self.__accountWiseLedgerList[key] = AccountWiseLedger.createByJsonBytes(json.dumps(self.__accountWiseLedgerList[key]))
                self.__vote = collections.Counter()

            self.printLog("Heard [Send AccountWiseLedgerList]")

        elif inputMsg["type"] == "New Transaction":
            print("Receive Task!")

    def __print(self, message, option="gui"):
        if option == "gui":
            self.__logFrame.append(message)
        elif option == "console":
            print(message)
        else:
            print("Wrong option")

    def getInputFromPopUpDialog(self, questionString):
        inputText, okPressed = QtWidgets.QInputDialog.getText(self, self.__programTitle, questionString, QtWidgets.QLineEdit.Normal, "")
        if okPressed and inputText:
            return inputText

    def dnsUpdateButtonHandler(self):
        outputMsg = {"type": "Request DNS Update", "senderID": self.__accountID}
        self.__send(outputMsg, self.__accountWiseLedgerDNS)

    def awlUpdateButtonHandler(self):
        self.__broadcast({"type": "Request AccountWiseLedgerList Update", "senderID": self.__accountID}, set(self.__accountSubNetwork))

    def newTransactionButtonHandler(self):
        task = {"senderID": self.__accountID}
        task["receiverID"] = input("The receiver's name: ")
        task["amount"] = input("The amount: ")

        self.__accountWiseLedgerList[self.__accountID].newTransaction(task)
        self.__broadcast({"type": "New Transaction", "data": task, "senderID": self.__accountID}, set(self.__accountSubNetwork))

    def printLog(self, eventTitle, option="gui"):
        logInformation = "<----" + eventTitle + "---->\n[VoteTable]: " + str(self.__vote) + "\n[All Node]: " + str(self.__nodeList) + "\n[AWL List]: " + str(self.__accountWiseLedgerList) + "\n<-------------------------->\n"
        self.__print(logInformation, option)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
