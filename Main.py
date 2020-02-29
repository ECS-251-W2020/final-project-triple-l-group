from AccountWiseLedger import *
from urllib.parse import urlencode
from io import BytesIO
import pycurl
import json
import socket
import sys
import collections
from time import time
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
        self.__socketBufferSize = 64 * 1024 * 1024

    def run(self):
        while True:
            while True:
                try:
                    self.__mutex.lock()
                    inputMsg, sourceAddress = self.__socket.recvfrom(self.__socketBufferSize)
                    inputMsg = json.loads(inputMsg)
                    self.__mutex.unlock()
                    break
                except:
                    pass

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
        self.__accountWiseLedgerDNS = ("192.168.0.29", 8000)
        self.__nodeList = {}
        self.__nodeLastBlockHash = {}
        self.__accountWiseLedgerList = {}
        self.__voteSenderBlock = collections.defaultdict(lambda: collections.defaultdict(set))
        self.__voteReceiverBlock = collections.defaultdict(lambda: collections.defaultdict(set))
        self.__voteValidTransaction = collections.defaultdict(lambda: collections.Counter())
        self.__voteAWL = collections.Counter()

        # Initialize the socket
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.bind((self.__getHostnameIP(), 0))

        # Initialize data
        self.__initData()

        # Initialize Multi-Threading for Listening
        self.__mutex = QMutex()
        self.__listenThread = ListenThread(self.__socket)
        self.__listenThread.listenedMsg.connect(self.__updateLocal)
        self.__listenThread.start()

        # Initialize Last Block Hash Table
        self.__broadcast({"type": "Request Last Block Hash", "senderID": self.__accountID}, set(self.__nodeList["all"].keys()))

        # Create Main Frame
        self.__centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(self.__centralWidget)
        self.setGeometry(self.__windowStartPositionX, self.__windowStartPositionY, self.__windowWidth, self.__windowHeight)
        self.setWindowTitle(self.__programTitle)

        # Menu Bar Actions
        menuBarAction_View_ShowMyData = QtWidgets.QAction("Show My Data", self)
        menuBarAction_View_ShowMyData.triggered.connect(lambda: self.printLog(""))

        # Create Menu Bar
        self.__menuBar = self.menuBar()
        self.__menuBar_View = self.__menuBar.addMenu("&View")
        self.__menuBar_View.addAction(menuBarAction_View_ShowMyData)

        # Create Transactions input Field and Current Balance
        self.__userInfoLabel = QtWidgets.QLabel(self)
        self.__userInfoLabel.setText("User: " + self.__accountID + "\t Sub-Network Index: " + self.__accountSubNetwork)
        self.__userBalance = QtWidgets.QLineEdit()
        self.__userBalance.setEnabled(False)
        self.__makeTransactionInputReceiverID = QtWidgets.QLineEdit()
        self.__makeTransactionInputAmount = QtWidgets.QLineEdit()
        self.__makeTransactionButton = QtWidgets.QPushButton("Make Transaction", self)
        self.__makeTransactionButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.__makeTransactionButton.clicked.connect(self.setTransactionButtonHandler)

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
        mainLayout.addWidget(self.__userBalance, 1, 2, 1, 1)
        mainLayout.addWidget(self.__makeTransactionInputReceiverID, 2, 2, 1, 1)
        mainLayout.addWidget(self.__makeTransactionInputAmount, 3, 2, 1, 1)
        mainLayout.addWidget(self.__makeTransactionButton, 1, 3, 3, 1)
        mainLayout.addWidget(self.__logFrame, 4, 2, 1, 2)
        mainLayout.addWidget(self.__dnsUpdateButton, 5, 0, 1, 1)
        mainLayout.addWidget(self.__awlUpdateButton, 5, 1, 1, 1)
        mainLayout.addWidget(self.__progressBar, 5, 2, 1, 2)

        self.__centralWidget.setLayout(mainLayout)
        self.show()

    def __initData(self):
        while True:
            try:
                self.__send({"type": "New Peer", "senderID": self.__accountID}, self.__accountWiseLedgerDNS)
                self.__nodeList = self.__listen()["data"]
                break
            except:
                pass

        self.__accountSubNetwork = str(self.__nodeList["nodeToSubNetwork"][self.__accountID])
        if len(self.__nodeList["subNetworkToNode"][self.__accountSubNetwork]) == 1:
            self.__accountWiseLedgerList[self.__accountID] = AccountWiseLedger(self.__accountID, self.__nodeList["nodeToSubNetwork"][self.__accountID])
            self.__nodeLastBlockHash[self.__accountID] = Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock)
            self.__broadcast({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, set(self.__nodeList["all"].keys()), True)
        self.awlUpdateButtonHandler()

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

    def __broadcast(self, outputMsg, targetMemberSet=None, meInclude=False):
        if targetMemberSet is None:
            for nodeID in self.__nodeList["all"].keys():
                if nodeID != self.__accountID or meInclude:
                    self.__send(outputMsg, tuple(self.__nodeList["all"][nodeID]))
        else:
            for nodeID in targetMemberSet:
                if nodeID != self.__accountID or meInclude:
                    self.__send(outputMsg, tuple(self.__nodeList["all"][nodeID]))

    def __updateLocal(self, inputMsg):
        if inputMsg["type"] == "New Peer ACK":
            self.__print("[" + inputMsg["senderID"] + "] says hi to me")

        elif inputMsg["type"] == "DNS update":
            self.__nodeList = inputMsg["data"]
            if inputMsg["newPeer"] is not None and str(self.__nodeList["nodeToSubNetwork"][inputMsg["newPeer"]]) == self.__accountSubNetwork:
                self.__accountWiseLedgerList[inputMsg["newPeer"]] = AccountWiseLedger(inputMsg["newPeer"], inputMsg["data"]["nodeToSubNetwork"][inputMsg["newPeer"]])
                self.__send({"type": "New Peer ACK", "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["newPeer"]]))

            self.__print("<DNS> gives me new update")

        elif inputMsg["type"] == "Request AWL List Update":
            transferedAWLL = {key: self.__accountWiseLedgerList[key].outputDict for key in self.__accountWiseLedgerList}
            self.__send({"type": "Send AWL List", "data": transferedAWLL, "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))
            self.__print("[" + inputMsg["senderID"] + "] asks for my AWL List")

        elif inputMsg["type"] == "Send AWL List":
            self.__voteAWL[json.dumps(inputMsg["data"]).encode()] += 1

            wonAWLL = max(self.__voteAWL.keys(), key=lambda x: (self.__voteAWL[x], len(x)))
            if self.__voteAWL[wonAWLL] > (len(self.__nodeList["subNetworkToNode"][self.__accountSubNetwork]) - 1) // 2:
                self.__accountWiseLedgerList = json.loads(wonAWLL)
                for key in self.__accountWiseLedgerList:
                    self.__accountWiseLedgerList[key] = AccountWiseLedger.createByJsonBytes(json.dumps(self.__accountWiseLedgerList[key]))
                self.__voteAWL = collections.Counter()
                self.__broadcast({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, set(self.__nodeList["all"].keys()), True)
                self.__userBalance.setText(str(self.__accountWiseLedgerList[self.__accountID].viewActualBalance))

            self.__print("[" + inputMsg["senderID"] + "] gives me its AWL List")

        elif inputMsg["type"] == "Request Last Block Hash":
            self.__send({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))
            self.__print("[" + inputMsg["senderID"] + "] asks for my Last Block Hash")

        elif inputMsg["type"] == "Send Last Block Hash":
            self.__nodeLastBlockHash[inputMsg["senderID"]] = inputMsg["data"]
            self.__print("[" + inputMsg["senderID"] + "] gives me its Last Block Hash")

        elif inputMsg["type"] == "New Transaction":
            if inputMsg["senderID"] == inputMsg["data"]["senderID"]:
                self.__print("[" + inputMsg["senderID"] + "] gives me a new task: [" + inputMsg["data"]["senderID"] + "] >> [" + inputMsg["data"]["receiverID"] + "] with $" + str(inputMsg["data"]["amount"]))
                highCouncilMemberDict = self.__highCouncilMemberElection(inputMsg["data"])

                if inputMsg["data"]["senderID"] in self.__accountWiseLedgerList:
                    self.__accountWiseLedgerList[inputMsg["data"]["senderID"]].setTransaction(inputMsg["data"], highCouncilMemberDict)
                if inputMsg["data"]["receiverID"] in self.__accountWiseLedgerList:
                    self.__accountWiseLedgerList[inputMsg["data"]["receiverID"]].setTransaction(inputMsg["data"], highCouncilMemberDict)
                self.__print("High Council Member: " + str(set(highCouncilMemberDict.keys())))

                if self.__accountID in highCouncilMemberDict:
                    self.__broadcast({"type": "Check Valid Transaction", "target": inputMsg["data"]["senderID"], "data": inputMsg["data"], "senderID": self.__accountID}, set(self.__nodeList["subNetworkToNode"][str(self.__nodeList["nodeToSubNetwork"][inputMsg["senderID"]])].keys()), True)

        elif inputMsg["type"] == "Check Valid Transaction":
            if str(self.__nodeList["nodeToSubNetwork"][inputMsg["target"]]) == self.__accountSubNetwork:
                if self.__accountWiseLedgerList[inputMsg["target"]].viewPlanningBalance >= 0:
                    self.__send({"type": "Ans Valid Transaction", "target": inputMsg["target"], "data": inputMsg["data"], "ans": "True", "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))
                    self.__print("[" + inputMsg["senderID"] + "] asks me the validity of: " + str(self.__accountWiseLedgerList[inputMsg["target"]].viewTransactionTask) + ". I said True")
                else:
                    self.__send({"type": "Ans Valid Transaction", "target": inputMsg["target"], "data": inputMsg["data"], "ans": "False", "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))
                    self.__print("[" + inputMsg["senderID"] + "] asks me the validity of: " + str(self.__accountWiseLedgerList[inputMsg["target"]].viewTransactionTask) + ". I said False")

        elif inputMsg["type"] == "Ans Valid Transaction":
            self.__voteValidTransaction[inputMsg["target"]][inputMsg["ans"]] += 1
            wonValidTransactionResult = max(self.__voteValidTransaction[inputMsg["target"]].keys(), key=lambda x: self.__voteValidTransaction[inputMsg["target"]][x])

            if self.__voteValidTransaction[inputMsg["target"]][wonValidTransactionResult] > (self.__nodeList["sizeOfSubNetwork"][self.__accountSubNetwork] - 1) // 2:
                if wonValidTransactionResult == "True":
                    senderSideBlock = self.__accountWiseLedgerList[self.__accountID].createNewBlock(inputMsg["data"], self.__nodeLastBlockHash[inputMsg["data"]["senderID"]])
                    receiverSideBlock = self.__accountWiseLedgerList[self.__accountID].createNewBlock(inputMsg["data"], self.__nodeLastBlockHash[inputMsg["data"]["receiverID"]])

                    self.__broadcast({"type": "New Block", "data": senderSideBlock, "memo": "Sender-Side-Block", "senderID": self.__accountID}, set(self.__nodeList["subNetworkToNode"][str(self.__nodeList["nodeToSubNetwork"][inputMsg["data"]["senderID"]])].keys()), True)
                    self.__broadcast({"type": "New Block", "data": receiverSideBlock, "memo": "Receiver-Side-Block", "senderID": self.__accountID}, set(self.__nodeList["subNetworkToNode"][str(self.__nodeList["nodeToSubNetwork"][inputMsg["data"]["receiverID"]])].keys()), True)
                    self.__print("<Sub-Network " + str(self.__nodeList["nodeToSubNetwork"][inputMsg["target"]]) + "> told me the transaction is valid.")
                else:
                    taskAbortSenderBlock = self.__accountWiseLedgerList[self.__accountID].createNewBlock(inputMsg["data"], self.__nodeLastBlockHash[inputMsg["data"]["senderID"]], taskAbortSignal=True)
                    taskAbortReceiverBlock = self.__accountWiseLedgerList[self.__accountID].createNewBlock(inputMsg["data"], self.__nodeLastBlockHash[inputMsg["data"]["receiverID"]], taskAbortSignal=True)
                    self.__broadcast({"type": "New Block", "data": taskAbortSenderBlock, "memo": "Sender-Side-Block", "senderID": self.__accountID}, set(self.__nodeList["subNetworkToNode"][str(self.__nodeList["nodeToSubNetwork"][inputMsg["data"]["senderID"]])].keys()), True)
                    self.__broadcast({"type": "New Block", "data": taskAbortReceiverBlock, "memo": "Receiver-Side-Block", "senderID": self.__accountID}, set(self.__nodeList["subNetworkToNode"][str(self.__nodeList["nodeToSubNetwork"][inputMsg["data"]["receiverID"]])].keys()), True)
                    self.__print("<Sub-Network " + str(self.__nodeList["nodeToSubNetwork"][inputMsg["target"]]) + "> told me the transaction is invalid.")

                del self.__voteValidTransaction[inputMsg["target"]]

        elif inputMsg["type"] == "New Block":
            if inputMsg["data"]["senderID"] in self.__accountWiseLedgerList and inputMsg["memo"] == "Sender-Side-Block":
                transactionTaskHandlerDict = self.__accountWiseLedgerList[inputMsg["data"]["senderID"]].viewTransactionTaskHandler
                transactopnTaskPowDifficulty = self.__accountWiseLedgerList[inputMsg["data"]["senderID"]].viewPowDifficulty
            elif inputMsg["data"]["receiverID"] in self.__accountWiseLedgerList and inputMsg["memo"] == "Receiver-Side-Block":
                transactionTaskHandlerDict = self.__accountWiseLedgerList[inputMsg["data"]["receiverID"]].viewTransactionTaskHandler
                transactopnTaskPowDifficulty = self.__accountWiseLedgerList[inputMsg["data"]["receiverID"]].viewPowDifficulty
            else:
                transactionTaskHandlerDict = {}
                transactopnTaskPowDifficulty = 0

            if inputMsg["senderID"] in transactionTaskHandlerDict and Blockchain.validBlock(inputMsg["data"], transactopnTaskPowDifficulty):
                self.__print("[" + inputMsg["senderID"] + "] gives me a " + inputMsg["memo"] + ": [" + inputMsg["data"]["senderID"] + "] >> [" + inputMsg["data"]["receiverID"] + "] with $" + str(inputMsg["data"]["amount"]))

                taskCode = json.dumps(self.__accountWiseLedgerList[inputMsg["data"]["senderID"]].viewTransactionTask if inputMsg["data"]["senderID"] in self.__accountWiseLedgerList else self.__accountWiseLedgerList[inputMsg["data"]["receiverID"]].viewTransactionTask).encode()
                resultCode = json.dumps({"senderID": inputMsg["data"]["senderID"], "receiverID": inputMsg["data"]["receiverID"], "amount": inputMsg["data"]["amount"], "preHash": inputMsg["data"]["preHash"]}).encode()

                if inputMsg["memo"] == "Sender-Side-Block" and inputMsg["data"]["senderID"] in self.__accountWiseLedgerList:
                    self.__voteSenderBlock[taskCode][resultCode].add(json.dumps(inputMsg["data"]))

                    wonSenderResult = max(self.__voteSenderBlock[taskCode].keys(), key=lambda x: len(x))
                    if len(self.__voteSenderBlock[taskCode][wonSenderResult]) > (len(transactionTaskHandlerDict) - 1) // 2:
                        attachedBlock = min(map(json.loads, self.__voteSenderBlock[taskCode][wonSenderResult]), key=lambda x: x["timestamp"])
                        if self.__accountWiseLedgerList[inputMsg["data"]["senderID"]].receiveResult(attachedBlock):
                            if inputMsg["data"]["senderID"] == self.__accountID:
                                self.__userBalance.setText(str(self.__accountWiseLedgerList[self.__accountID].viewActualBalance))
                                self.__broadcast({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, self.__nodeList["all"].keys(), True)
                        else:
                            self.__print("<High Council> told me this task is invalid. Therefore, task abort")
                        del self.__voteSenderBlock[taskCode]

                if inputMsg["memo"] == "Receiver-Side-Block" and inputMsg["data"]["receiverID"] in self.__accountWiseLedgerList:
                    self.__voteReceiverBlock[taskCode][resultCode].add(json.dumps(inputMsg["data"]))

                    wonReceiverResult = max(self.__voteReceiverBlock[taskCode].keys(), key=lambda x: len(x))
                    if len(self.__voteReceiverBlock[taskCode][wonReceiverResult]) > (len(transactionTaskHandlerDict) - 1) // 2:
                        attachedBlock = min(map(json.loads, self.__voteReceiverBlock[taskCode][wonReceiverResult]), key=lambda x: x["timestamp"])
                        if self.__accountWiseLedgerList[inputMsg["data"]["receiverID"]].receiveResult(attachedBlock):
                            if inputMsg["data"]["receiverID"] == self.__accountID:
                                self.__userBalance.setText(str(self.__accountWiseLedgerList[self.__accountID].viewActualBalance))
                                self.__broadcast({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, self.__nodeList["all"].keys(), True)
                        else:
                            self.__print("<High Council> told me this task is invalid. Therefore, task abort")
                        del self.__voteReceiverBlock[taskCode]

    def __print(self, message, option="gui"):
        if option == "gui":
            self.__logFrame.append(message)
        elif option == "console":
            print(message)
        else:
            print("Wrong option")

    def __highCouncilMemberElection(self, task):
        highCouncilMember, taskHashInt = {}, int(Blockchain.hash256(task), 16)

        for subNetwork in self.__nodeList["subNetworkToIndex"].keys():
            if self.__nodeList["sizeOfSubNetwork"][subNetwork] > 2:
                designatedMember = self.__nodeList["subNetworkToIndex"][subNetwork][str(taskHashInt % len(self.__nodeList["subNetworkToIndex"][subNetwork]))]
                if designatedMember == task["senderID"] or designatedMember == task["receiverID"]:
                    if task["senderID"] in self.__nodeList["subNetworkToNode"][subNetwork] and task["receiverID"] in self.__nodeList["subNetworkToNode"][subNetwork]:
                        indexDelta = abs(self.__nodeList["subNetworkToNode"][subNetwork][task["senderID"]] - self.__nodeList["subNetworkToNode"][subNetwork][task["receiverID"]])
                        if indexDelta > 1:
                            designatedMember = self.__nodeList["subNetworkToIndex"][subNetwork][str((taskHashInt % (indexDelta - 1) + 1 + min(self.__nodeList["subNetworkToNode"][subNetwork][task["senderID"]], self.__nodeList["subNetworkToNode"][subNetwork][task["receiverID"]])))]
                        elif self.__nodeList["subNetworkToNode"][subNetwork][designatedMember] >= self.__nodeList["subNetworkToNode"][subNetwork][task["receiverID"]] and self.__nodeList["subNetworkToNode"][subNetwork][designatedMember] >= self.__nodeList["subNetworkToNode"][subNetwork][task["senderID"]]:
                            designatedMember = self.__nodeList["subNetworkToIndex"][subNetwork][str(((taskHashInt - 2) % len(self.__nodeList["subNetworkToIndex"][subNetwork])))]
                        else:
                            designatedMember = self.__nodeList["subNetworkToIndex"][subNetwork][str(((taskHashInt + 2) % len(self.__nodeList["subNetworkToIndex"][subNetwork])))]
                    else:
                        designatedMember = self.__nodeList["subNetworkToIndex"][subNetwork][str(taskHashInt % (len(self.__nodeList["subNetworkToIndex"][subNetwork]) - 1))]

                highCouncilMember[designatedMember] = True

        return highCouncilMember

    def getInputFromPopUpDialog(self, questionString):
        inputText, okPressed = QtWidgets.QInputDialog.getText(self, self.__programTitle, questionString, QtWidgets.QLineEdit.Normal, "")
        if okPressed and inputText:
            return inputText

    def dnsUpdateButtonHandler(self):
        outputMsg = {"type": "Request DNS Update", "senderID": self.__accountID}
        self.__send(outputMsg, self.__accountWiseLedgerDNS)

    def awlUpdateButtonHandler(self):
        self.__broadcast({"type": "Request AWL List Update", "senderID": self.__accountID}, set(self.__nodeList["subNetworkToNode"][self.__accountSubNetwork].keys()))

    def setTransactionButtonHandler(self):
        try:
            if self.__nodeList["sizeOfSubNetwork"][self.__accountSubNetwork] < 3:
                QtWidgets.QMessageBox.warning(self, self.__programTitle, "There are less than 3 peers in your Sub-Network. Transactions are not allowed for now.", QtWidgets.QMessageBox.Ok)
                self.__makeTransactionInputAmount.setText("")
                self.__makeTransactionInputReceiverID.setText("")
            elif int(self.__makeTransactionInputAmount.text()) > 0 and self.__makeTransactionInputReceiverID.text() != self.__accountID:
                task = {"senderID": self.__accountID, "receiverID": self.__makeTransactionInputReceiverID.text(), "amount": int(self.__makeTransactionInputAmount.text()), "timestamp": time()}

                broadcastSubNetworkIndex = {self.__accountSubNetwork, str(self.__nodeList["nodeToSubNetwork"][task["receiverID"]])}
                for subNetworkIndex in broadcastSubNetworkIndex:
                    self.__broadcast({"type": "New Transaction", "data": task, "senderID": self.__accountID}, set(self.__nodeList["subNetworkToNode"][subNetworkIndex].keys()), True)
            elif self.__makeTransactionInputReceiverID.text() == self.__accountID:
                QtWidgets.QMessageBox.warning(self, self.__programTitle, "Transferring amount to yourself is not allowed.", QtWidgets.QMessageBox.Ok)
                self.__makeTransactionInputAmount.setText("")
                self.__makeTransactionInputReceiverID.setText("")
            else:
                QtWidgets.QMessageBox.warning(self, self.__programTitle, "Negative or Null amount is not allowed.", QtWidgets.QMessageBox.Ok)
                self.__makeTransactionInputAmount.setText("")
                self.__makeTransactionInputReceiverID.setText("")

        except KeyError:
            QtWidgets.QMessageBox.warning(self, self.__programTitle, "The receiver does not exist.", QtWidgets.QMessageBox.Ok)
            self.__makeTransactionInputAmount.setText("")
            self.__makeTransactionInputReceiverID.setText("")

        except ValueError:
            QtWidgets.QMessageBox.warning(self, self.__programTitle, "Please insert valid number.", QtWidgets.QMessageBox.Ok)
            self.__makeTransactionInputAmount.setText("")
            self.__makeTransactionInputReceiverID.setText("")

    def printLog(self, eventTitle, option="gui"):
        logInformation = eventTitle + \
                         "\n<-------MY CURRENT DATA------->" \
                         "\n[Vote AWL]: " + str(self.__voteAWL) + \
                         "\n[Vot SBLK]: " + str(self.__voteSenderBlock) + \
                         "\n[Vot RBLK]: " + str(self.__voteReceiverBlock) + \
                         "\n[LST HASH]: " + str(self.__nodeLastBlockHash) + \
                         "\n[All Node]: " + str(self.__nodeList) + \
                         "\n[AWL List]: " + str(self.__accountWiseLedgerList) + \
                         "\n<-------------END------------->\n"
        self.__print(logInformation, option)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
