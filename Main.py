from AccountWiseLedger import *
import json
import socket
import sys
import collections
import time
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QThread, pyqtSignal, QMutex

SOCKET_BUFFER_SIZE = 64 * 1024 * 1024


class MyListenThread(QThread):
    listenedMsg = pyqtSignal(dict)

    def __init__(self, parent, title, mySocket, timeout=None):
        super(MyListenThread, self).__init__()
        self.__mainWindow = parent
        self.__programTitle = title

        self.__mutex = QMutex()
        self.__socket = mySocket
        self.__socketTimeout = timeout

    def run(self):
        while True:
            self.__mutex.lock()
            inputMsg = MyListenThread.listen(self.__mainWindow, self.__programTitle, self.__socket, SOCKET_BUFFER_SIZE, self.__socketTimeout)
            self.__mutex.unlock()

            self.listenedMsg.emit(inputMsg)

    @staticmethod
    def listen(parent, title, mySocket, socketBufferSize, timeout=None):
        inputMsg = None
        mySocket.settimeout(timeout)

        while not inputMsg:
            try:
                inputMsg, sourceAddress = mySocket.recvfrom(socketBufferSize)
                inputMsg = json.loads(inputMsg)
            except (ConnectionResetError, socket.timeout):
                QtWidgets.QMessageBox.warning(parent, title, "The remote endpoint has no response. Please check your connection settings.", QtWidgets.QMessageBox.Ok)
                sys.exit(0)

        mySocket.settimeout(None)
        return inputMsg


class MyProgressBar(QtWidgets.QProgressBar):

    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self._text = None

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text


class MyInputDialog(QtWidgets.QDialog):

    def __init__(self, parent, programTitle, questions, defaultAns=None):
        super(MyInputDialog, self).__init__(parent)
        self.questions = [QtWidgets.QLabel(self) for _ in range(len(questions))]
        self.ans = [QtWidgets.QLineEdit() for _ in range(len(questions))]
        self.reply = None
        self.setWindowTitle(programTitle)

        self.__mainFrame = QtWidgets.QFrame()
        mainFrameLayout = QtWidgets.QGridLayout()
        for index, question in enumerate(questions):
            self.questions[index].setText(question)
            if defaultAns:
                self.ans[index].setText(defaultAns[index])
            mainFrameLayout.addWidget(self.questions[index], index, 0)
            mainFrameLayout.addWidget(self.ans[index], index, 1)

        self.__mainFrame.setLayout(mainFrameLayout)

        self.__okButton = QtWidgets.QPushButton("OK", self)
        self.__okButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.__okButton.clicked.connect(lambda: self._btnHandler(True))

        self.__cancelButton = QtWidgets.QPushButton("Cancel", self)
        self.__cancelButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.__cancelButton.clicked.connect(lambda: self._btnHandler(False))

        mainLayout = QtWidgets.QGridLayout()
        mainLayout.addWidget(self.__mainFrame, 0, 0, 1, 2)
        mainLayout.addWidget(self.__okButton, 1, 0, 1, 1)
        mainLayout.addWidget(self.__cancelButton, 1, 1, 1, 1)

        self.setLayout(mainLayout)

    @classmethod
    def getText(cls, parent, programTitle, questions, defaultAns=None):
        dialog = cls(parent, programTitle, questions, defaultAns)
        dialog.exec_()
        return dialog.ans, dialog.reply

    def _btnHandler(self, reply):
        self.ans = [ansSlot.text() for ansSlot in self.ans]
        self.reply = reply
        self.close()


class UserInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super(UserInterface, self).__init__()
        self.__desktop = QtWidgets.QApplication.desktop()
        self.__screenRectangle = self.__desktop.screenGeometry(self.__desktop.screenNumber(QtGui.QCursor.pos()))
        self.__windowStartPositionX = 150
        self.__windowStartPositionY = 100
        self.__windowHeight = 600
        self.__windowWidth = 1000
        self.__programTitle = "Account Wise Ledger User Interface"

        [self.__accountID, dnsIP, dnsPort], okPressed = MyInputDialog.getText(self, self.__programTitle, ["Your Name:", "DNS IP:", "DNS Port:"], [socket.gethostname(), self.__getHostnameIP(), "8000"])
        if not okPressed:
            sys.exit(0)

        self.__accountSubNetwork = ""
        self.__accountWiseLedgerDNS = (dnsIP, int(dnsPort))
        self.__nodeList = {}
        self.__nodeLastBlockHash = {}
        self.__accountWiseLedgerList = {}
        self.__voteSenderBlock = collections.defaultdict(lambda: collections.defaultdict(set))
        self.__voteReceiverBlock = collections.defaultdict(lambda: collections.defaultdict(set))
        self.__voteValidTransaction = collections.defaultdict(lambda: collections.Counter())
        self.__voteAWL = collections.Counter()

        # Initialize the socket
        self.__ip = self.__getHostnameIP()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.bind((self.__ip, 0))
        self.__socketTimeout = 3

        # Initialize data
        self.__initData()

        # Initialize Multi-Threading for Listening
        self.__mutex = QMutex()
        self.__listenThread = MyListenThread(self, self.__programTitle, self.__socket)
        self.__listenThread.listenedMsg.connect(self.__listen)
        self.__listenThread.start()

        # Initialize Last Block Hash Table
        self.__broadcast({"type": "Request Last Block Hash", "senderID": self.__accountID}, set(self.__nodeList["all"].keys()))

        # Create Main Frame
        self.__centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(self.__centralWidget)
        self.setGeometry(self.__windowStartPositionX, self.__windowStartPositionY, self.__windowWidth, self.__windowHeight)
        self.setWindowTitle(self.__programTitle)

        # Create Sub-Frame
        self.__leftFrame = QtWidgets.QFrame()
        self.__rightFrame = QtWidgets.QFrame()

        # Create Sub-Frame Splitter
        self.__hSplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.__hSplitter.addWidget(self.__leftFrame)
        self.__hSplitter.addWidget(self.__rightFrame)

        # Menu Bar Actions
        menuBarAction_View_ShowMyData = QtWidgets.QAction("Show My Data", self)
        menuBarAction_View_ShowMyData.triggered.connect(lambda: self.printLog(""))
        menuBarAction_View_CleanLog = QtWidgets.QAction("Clean Logs", self)
        menuBarAction_View_CleanLog.triggered.connect(lambda: self.__logFrame.setText(""))

        # Create Menu Bar
        self.__menuBar = self.menuBar()
        self.__menuBar_View = self.__menuBar.addMenu("&View")
        self.__menuBar_View.addAction(menuBarAction_View_ShowMyData)
        self.__menuBar_View.addAction(menuBarAction_View_CleanLog)

        # Create Transactions input Field and Current Balance
        self.__userInfoLabel = QtWidgets.QLabel(self)
        self.__userInfoLabel.setText("User ID: " + self.__accountID + "\t Sub-Network Index: " + self.__accountSubNetwork)
        self.__userBalanceLabel = QtWidgets.QLabel(self)
        self.__userBalanceLabel.setText("Your Balance")
        self.__userBalance = QtWidgets.QLineEdit()
        try:
            self.__userBalance.setText(str(self.__accountWiseLedgerList[self.__accountID].viewActualBalance))
        except KeyError:
            pass
        finally:
            self.__userBalance.setEnabled(False)
        self.__makeTransactionInputReceiverIDLabel = QtWidgets.QLabel(self)
        self.__makeTransactionInputReceiverIDLabel.setText("Receiver ID")
        self.__makeTransactionInputReceiverID = QtWidgets.QLineEdit()
        self.__makeTransactionInputAmountIDLabel = QtWidgets.QLabel(self)
        self.__makeTransactionInputAmountIDLabel.setText("Amount")
        self.__makeTransactionInputAmount = QtWidgets.QLineEdit()
        self.__makeTransactionButton = QtWidgets.QPushButton("Make Transaction", self)
        self.__makeTransactionButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.__makeTransactionButton.clicked.connect(self.setTransactionButtonHandler)

        # Create Peers Table
        self.__peersTableHeader = {"User ID": 0, "IP Address": 1, "Port": 2, "SN": 3}
        self.__peersTable = QtWidgets.QTableWidget(0, len(self.__peersTableHeader))
        self.__peersTable.setHorizontalHeaderLabels(self.__peersTableHeader.keys())
        for peersTableHeaderIndex in range(0, len(self.__peersTableHeader)):
            self.__peersTable.horizontalHeader().setSectionResizeMode(peersTableHeaderIndex, QtWidgets.QHeaderView.ResizeToContents)
        self.__peersTable.horizontalHeader().setSectionResizeMode(self.__peersTableHeader["IP Address"], QtWidgets.QHeaderView.Stretch)
        self.__updatePeersTable()

        # Create Transactions Histories Table
        self.__transactionHistoriesTableHeader = {"Sender ID": 0, "Receiver ID": 1, "Amount": 2, "Time": 3}
        self.__transactionHistoriesTable = QtWidgets.QTableWidget(0, len(self.__transactionHistoriesTableHeader))
        self.__transactionHistoriesTable.setHorizontalHeaderLabels(self.__transactionHistoriesTableHeader.keys())
        for transactionHistoriesTableHeaderIndex in range(0, len(self.__transactionHistoriesTableHeader)):
            self.__transactionHistoriesTable.horizontalHeader().setSectionResizeMode(transactionHistoriesTableHeaderIndex, QtWidgets.QHeaderView.ResizeToContents)
        self.__transactionHistoriesTable.horizontalHeader().setSectionResizeMode(self.__transactionHistoriesTableHeader["Time"], QtWidgets.QHeaderView.Stretch)

        # Create Tabs for Peers Table and Personal Transaction Histories
        self.__tabs = QtWidgets.QTabWidget()
        self.__tabs.addTab(self.__peersTable, "Peers")
        self.__tabs.addTab(self.__transactionHistoriesTable, "My Transactions")

        # Create Log Frame
        self.__logFrame = QtWidgets.QTextBrowser(self)

        # Create Buttons
        self.__awlUpdateButton = QtWidgets.QPushButton("Update AWL List", self)
        self.__awlUpdateButton.clicked.connect(self.awlUpdateButtonHandler)
        self.__dnsUpdateButton = QtWidgets.QPushButton("Update Peer List", self)
        self.__dnsUpdateButton.clicked.connect(self.dnsUpdateButtonHandler)

        # Create Progress Bar
        self.__progressBar = MyProgressBar()

        # Manage the layout
        leftLayout = QtWidgets.QGridLayout()
        leftLayout.addWidget(self.__tabs, 0, 0, 1, 2)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        self.__leftFrame.setLayout(leftLayout)

        rightLayout = QtWidgets.QGridLayout()
        rightLayout.addWidget(self.__userInfoLabel, 0, 0, 1, 2)
        rightLayout.addWidget(self.__userBalanceLabel, 1, 0, 1, 1)
        rightLayout.addWidget(self.__userBalance, 1, 1, 1, 1)
        rightLayout.addWidget(self.__makeTransactionInputReceiverIDLabel, 2, 0, 1, 1)
        rightLayout.addWidget(self.__makeTransactionInputReceiverID, 2, 1, 1, 1)
        rightLayout.addWidget(self.__makeTransactionInputAmountIDLabel, 3, 0, 1, 1)
        rightLayout.addWidget(self.__makeTransactionInputAmount, 3, 1, 1, 1)
        rightLayout.addWidget(self.__makeTransactionButton, 1, 2, 3, 1)
        rightLayout.addWidget(self.__logFrame, 4, 0, 1, 3)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        self.__rightFrame.setLayout(rightLayout)

        mainLayout = QtWidgets.QGridLayout()
        mainLayout.addWidget(self.__hSplitter, 0, 0, 1, 3)
        mainLayout.addWidget(self.__dnsUpdateButton, 1, 0, 1, 1)
        mainLayout.addWidget(self.__awlUpdateButton, 1, 1, 1, 1)
        mainLayout.addWidget(self.__progressBar, 1, 2, 1, 1)

        self.__centralWidget.setLayout(mainLayout)
        self.show()

    def __initData(self):
        while True:
            try:
                self.__send({"type": "New Peer", "senderID": self.__accountID}, self.__accountWiseLedgerDNS)
                self.__nodeList = MyListenThread.listen(self, self.__programTitle, self.__socket, SOCKET_BUFFER_SIZE, 3)["data"]
                break
            except KeyError:
                pass

        self.__accountSubNetwork = str(self.__nodeList["nodeToSubNetwork"][self.__accountID])
        if len(self.__nodeList["subNetworkToNode"][self.__accountSubNetwork]) == 1:
            self.__accountWiseLedgerList[self.__accountID] = AccountWiseLedger(self.__accountID, self.__nodeList["nodeToSubNetwork"][self.__accountID])
            self.__nodeLastBlockHash[self.__accountID] = Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock)
            self.__broadcast({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, set(self.__nodeList["all"].keys()), True)
        self.awlUpdateButtonHandler()

    def __getHostnameIP(self):
        try:
            tmpS = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tmpS.connect(("8.8.8.8", 80))
            ans = tmpS.getsockname()[0]
            tmpS.close()
            return ans
        except:
            return None

    def __send(self, outputMsg, ipPortTuple):
        self.__socket.sendto(json.dumps(outputMsg).encode(), ipPortTuple)
        return

    def __broadcast(self, outputMsg, targetMemberSet=None, meInclude=False):
        for nodeID in targetMemberSet if targetMemberSet else self.__nodeList["all"].keys():
            if nodeID != self.__accountID or meInclude:
                self.__send(outputMsg, tuple(self.__nodeList["all"][nodeID]))

    def __listen(self, inputMsg):
        if inputMsg["type"] == "New Peer ACK":
            self.__print("[" + inputMsg["senderID"] + "] says hi to me")

        elif inputMsg["type"] == "DNS update":
            self.__nodeList = inputMsg["data"]
            if inputMsg["newPeer"] is not None and str(self.__nodeList["nodeToSubNetwork"][inputMsg["newPeer"]]) == self.__accountSubNetwork:
                self.__accountWiseLedgerList[inputMsg["newPeer"]] = AccountWiseLedger(inputMsg["newPeer"], inputMsg["data"]["nodeToSubNetwork"][inputMsg["newPeer"]])
                self.__send({"type": "New Peer ACK", "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["newPeer"]]))
            self.__updatePeersTable()

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
                self.__updateTransactionHistoriesTable()

            self.__print("[" + inputMsg["senderID"] + "] gives me its AWL List")

        elif inputMsg["type"] == "Request Last Block Hash":
            self.__send({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))
            self.__print("[" + inputMsg["senderID"] + "] asks for my Last Block Hash")

        elif inputMsg["type"] == "Send Last Block Hash":
            self.__nodeLastBlockHash[inputMsg["senderID"]] = inputMsg["data"]
            self.__print("[" + inputMsg["senderID"] + "] gives me its Last Block Hash")

        elif inputMsg["type"] == "Request Receiver ACK":
            if self.__accountID == inputMsg["data"]["receiverID"]:
                self.__print("[" + inputMsg["senderID"] + "] asks my ACK of a new task: [" + inputMsg["data"]["senderID"] + "] >> [" + inputMsg["data"]["receiverID"] + "] with $" + str(inputMsg["data"]["amount"]))
                self.__progressBar.setText("")
                self.__progressBar.setMaximum(len(self.__nodeList["sizeOfSubNetwork"]) + ((2 * ((self.__nodeList["sizeOfSubNetwork"][self.__accountSubNetwork] - 1) // 2)) if str(self.__nodeList["nodeToSubNetwork"][inputMsg["data"]["senderID"]]) == self.__accountSubNetwork else ((self.__nodeList["sizeOfSubNetwork"][self.__accountSubNetwork] - 1) // 2)))
                self.__progressBar.setValue(0)
                self.__makeTransactionInputReceiverID.setEnabled(False)
                self.__makeTransactionInputAmount.setEnabled(False)

                inputMsg["data"].update({"receiverSignature": self.__accountID})
                self.__send({"type": "Send Receiver ACK", "data": inputMsg["data"], "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))

        elif inputMsg["type"] == "Send Receiver ACK":
            if inputMsg["data"]["senderID"] == self.__accountID and inputMsg["data"]["receiverID"] == self.__makeTransactionInputReceiverID.text() and inputMsg["data"]["amount"] == int(self.__makeTransactionInputAmount.text()):
                self.__print("[" + inputMsg["senderID"] + "] gives me its ACK of a new task: [" + inputMsg["data"]["senderID"] + "] >> [" + inputMsg["data"]["receiverID"] + "] with $" + str(inputMsg["data"]["amount"]))
                broadcastSubNetworkIndex = {self.__accountSubNetwork, str(self.__nodeList["nodeToSubNetwork"][inputMsg["data"]["receiverID"]])}
                for subNetworkIndex in broadcastSubNetworkIndex:
                    self.__broadcast({"type": "New Transaction", "data": inputMsg["data"], "senderID": self.__accountID}, set(self.__nodeList["subNetworkToNode"][subNetworkIndex].keys()), True)

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
                if self.__accountWiseLedgerList[inputMsg["target"]].viewPlanningBalance >= 0 and inputMsg["data"]["amount"] > 0 and inputMsg["data"]["receiverSignature"] == inputMsg["data"]["receiverID"]:
                    self.__send({"type": "Ans Valid Transaction", "target": inputMsg["target"], "data": inputMsg["data"], "ans": "True", "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))
                    self.__print("[" + inputMsg["senderID"] + "] asks me the validity of: [" + inputMsg["data"]["senderID"] + "] >> [" + inputMsg["data"]["receiverID"] + "] with $" + str(inputMsg["data"]["amount"]) + ". I said Yes")
                else:
                    self.__send({"type": "Ans Valid Transaction", "target": inputMsg["target"], "data": inputMsg["data"], "ans": "False", "senderID": self.__accountID}, tuple(self.__nodeList["all"][inputMsg["senderID"]]))
                    self.__print("[" + inputMsg["senderID"] + "] asks me the validity of: [" + inputMsg["data"]["senderID"] + "] >> [" + inputMsg["data"]["receiverID"] + "] with $" + str(inputMsg["data"]["amount"]) + ". I said No")

        elif inputMsg["type"] == "Ans Valid Transaction":
            self.__voteValidTransaction[inputMsg["target"]][inputMsg["ans"]] += 1
            wonValidTransactionResult = max(self.__voteValidTransaction[inputMsg["target"]].keys(), key=lambda x: self.__voteValidTransaction[inputMsg["target"]][x])

            if self.__voteValidTransaction[inputMsg["target"]][wonValidTransactionResult] > (self.__nodeList["sizeOfSubNetwork"][self.__accountSubNetwork] - 1) // 2:
                if wonValidTransactionResult == "True" and inputMsg["data"]["receiverSignature"] == inputMsg["data"]["receiverID"]:
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
                    if self.__accountID == inputMsg["data"]["senderID"] or self.__accountID == inputMsg["data"]["receiverID"]:
                        self.__progressBar.setValue(self.__progressBar.value() + 1)

                    wonSenderResult = max(self.__voteSenderBlock[taskCode].keys(), key=lambda x: len(x))
                    if len(self.__voteSenderBlock[taskCode][wonSenderResult]) > (len(transactionTaskHandlerDict) - 1) // 2:
                        attachedBlock = min(map(json.loads, self.__voteSenderBlock[taskCode][wonSenderResult]), key=lambda x: x["timestamp"])
                        if self.__accountWiseLedgerList[inputMsg["data"]["senderID"]].receiveResult(attachedBlock):
                            if inputMsg["data"]["senderID"] == self.__accountID:
                                self.__userBalance.setText(str(self.__accountWiseLedgerList[self.__accountID].viewActualBalance))
                                self.__updateTransactionHistoriesTable()
                                self.__broadcast({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, self.__nodeList["all"].keys(), True)
                                self.__progressBar.setText("Task Complete")
                                self.__progressBar.reset()
                                self.__makeTransactionInputReceiverID.setEnabled(True)
                                self.__makeTransactionInputAmount.setEnabled(True)
                        else:
                            if inputMsg["data"]["senderID"] == self.__accountID:
                                self.__progressBar.setText("Task Incomplete")
                                self.__progressBar.reset()
                                self.__makeTransactionInputReceiverID.setEnabled(True)
                                self.__makeTransactionInputAmount.setEnabled(True)
                            self.__print("<High Council> told me this task is invalid. Therefore, task abort")
                        del self.__voteSenderBlock[taskCode]

                if inputMsg["memo"] == "Receiver-Side-Block" and inputMsg["data"]["receiverID"] in self.__accountWiseLedgerList:
                    self.__voteReceiverBlock[taskCode][resultCode].add(json.dumps(inputMsg["data"]))
                    if self.__accountID == inputMsg["data"]["senderID"] or self.__accountID == inputMsg["data"]["receiverID"]:
                        self.__progressBar.setValue(self.__progressBar.value() + 1)

                    wonReceiverResult = max(self.__voteReceiverBlock[taskCode].keys(), key=lambda x: len(x))
                    if len(self.__voteReceiverBlock[taskCode][wonReceiverResult]) > (len(transactionTaskHandlerDict) - 1) // 2:
                        attachedBlock = min(map(json.loads, self.__voteReceiverBlock[taskCode][wonReceiverResult]), key=lambda x: x["timestamp"])
                        if self.__accountWiseLedgerList[inputMsg["data"]["receiverID"]].receiveResult(attachedBlock):
                            if inputMsg["data"]["receiverID"] == self.__accountID:
                                self.__userBalance.setText(str(self.__accountWiseLedgerList[self.__accountID].viewActualBalance))
                                self.__updateTransactionHistoriesTable()
                                self.__broadcast({"type": "Send Last Block Hash", "data": Blockchain.hash256(self.__accountWiseLedgerList[self.__accountID].viewLastBlock), "senderID": self.__accountID}, self.__nodeList["all"].keys(), True)
                                self.__progressBar.setText("Task Complete")
                                self.__progressBar.reset()
                                self.__makeTransactionInputReceiverID.setEnabled(True)
                                self.__makeTransactionInputAmount.setEnabled(True)
                        else:
                            if inputMsg["data"]["receiverID"] == self.__accountID:
                                self.__progressBar.setText("Task Incomplete")
                                self.__progressBar.reset()
                                self.__makeTransactionInputReceiverID.setEnabled(True)
                                self.__makeTransactionInputAmount.setEnabled(True)
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

            if self.__accountID == task["senderID"] or self.__accountID == task["receiverID"]:
                self.__progressBar.setValue(self.__progressBar.value() + 1)

        return highCouncilMember

    def __updatePeersTable(self):
        for rowIndex, peersID in enumerate(self.__nodeList["all"].keys()):
            self.__peersTable.setRowCount(rowIndex + 1)
            self.__peersTable.setItem(rowIndex, self.__peersTableHeader["User ID"], QtWidgets.QTableWidgetItem(peersID))
            self.__peersTable.setItem(rowIndex, self.__peersTableHeader["IP Address"], QtWidgets.QTableWidgetItem(self.__nodeList["all"][peersID][0]))
            self.__peersTable.setItem(rowIndex, self.__peersTableHeader["Port"], QtWidgets.QTableWidgetItem(str(self.__nodeList["all"][peersID][1])))
            self.__peersTable.setItem(rowIndex, self.__peersTableHeader["SN"], QtWidgets.QTableWidgetItem(str(self.__nodeList["nodeToSubNetwork"][peersID])))

    def __updateTransactionHistoriesTable(self):
        for rowIndex, transaction in enumerate(self.__accountWiseLedgerList[self.__accountID].viewBlockchain[1:]):
            self.__transactionHistoriesTable.setRowCount(rowIndex + 1)
            self.__transactionHistoriesTable.setItem(rowIndex, self.__transactionHistoriesTableHeader["Sender ID"], QtWidgets.QTableWidgetItem(transaction["senderID"]))
            self.__transactionHistoriesTable.setItem(rowIndex, self.__transactionHistoriesTableHeader["Receiver ID"], QtWidgets.QTableWidgetItem(transaction["receiverID"]))
            self.__transactionHistoriesTable.setItem(rowIndex, self.__transactionHistoriesTableHeader["Amount"], QtWidgets.QTableWidgetItem(str(transaction["amount"])))
            self.__transactionHistoriesTable.setItem(rowIndex, self.__transactionHistoriesTableHeader["Time"], QtWidgets.QTableWidgetItem(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(transaction["timestamp"]))))

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
            elif not self.__makeTransactionInputReceiverID.isEnabled() or not self.__makeTransactionInputAmount.isEnabled():
                self.__print("************THE SYSTEM IS BUSY**************")

            elif 0 < int(self.__makeTransactionInputAmount.text()) <= self.__accountWiseLedgerList[self.__accountID].viewPlanningBalance and self.__makeTransactionInputReceiverID.text() != self.__accountID:
                newTask = {"senderID": self.__accountID, "receiverID": self.__makeTransactionInputReceiverID.text(), "amount": int(self.__makeTransactionInputAmount.text()), "timestamp": time.time()}
                self.__send({"type": "Request Receiver ACK", "data": newTask, "senderID": self.__accountID}, tuple(self.__nodeList["all"][self.__makeTransactionInputReceiverID.text()]))

                self.__makeTransactionInputReceiverID.setEnabled(False)
                self.__makeTransactionInputAmount.setEnabled(False)
                self.__progressBar.setText("")
                self.__progressBar.setMaximum(len(self.__nodeList["sizeOfSubNetwork"]) + ((2 * ((self.__nodeList["sizeOfSubNetwork"][self.__accountSubNetwork] - 1) // 2)) if str(self.__nodeList["nodeToSubNetwork"][self.__makeTransactionInputReceiverID.text()]) == self.__accountSubNetwork else ((self.__nodeList["sizeOfSubNetwork"][self.__accountSubNetwork] - 1) // 2)))
                self.__progressBar.setValue(0)

            elif self.__makeTransactionInputReceiverID.text() == self.__accountID:
                QtWidgets.QMessageBox.warning(self, self.__programTitle, "Transferring amount to yourself is not allowed.", QtWidgets.QMessageBox.Ok)
                self.__makeTransactionInputAmount.setText("")
                self.__makeTransactionInputReceiverID.setText("")
            else:
                QtWidgets.QMessageBox.warning(self, self.__programTitle, "The inserted amount is invalid.", QtWidgets.QMessageBox.Ok)
                self.__makeTransactionInputAmount.setText("")
                self.__makeTransactionInputReceiverID.setText("")

        except KeyError:
            QtWidgets.QMessageBox.warning(self, self.__programTitle, "The receiver does not exist.", QtWidgets.QMessageBox.Ok)
            self.__makeTransactionInputAmount.setText("")
            self.__makeTransactionInputReceiverID.setText("")

        except ValueError:
            QtWidgets.QMessageBox.warning(self, self.__programTitle, "Please insert a number in the amount slot.", QtWidgets.QMessageBox.Ok)
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
