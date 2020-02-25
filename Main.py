from AccountWiseLedger import AccountWiseLedger
from flask import Flask, request
from argparse import ArgumentParser
from urllib.parse import urlencode
from io import BytesIO
import pycurl
import json
import socket
import threading
import sys
import os
from distutils.util import strtobool
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


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
            inputMsg = json.loads(inputMsg.decode())
            self.__mutex.unlock()

            self.listenedMsg.emit(inputMsg)


class UserInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super(UserInterface, self).__init__()
        self.__windowStartPositionX = 150
        self.__windowStartPositionY = 100
        self.__windowHeight = 600
        self.__windowWidth = 1000
        self.__programTitle = "User Interface"

        self.__accountID = "AAA"
        self.__accountAddress = ""
        self.__accountWiseLedgerDNS = ("192.168.0.29", 8000)
        self.__accountWiseLedgerList = {}

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.bind((self.__getHostnameIP(), 5000))

        self.__listenThread = ListenThread(self.__socket)
        self.__listenThread.listenedMsg.connect(self.__listen)
        self.__listenThread.start()

        self.__send(json.dumps({"type": "New Peer", "data": self.__accountID}), self.__accountWiseLedgerDNS)

        # Create Main Frame
        self.__centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(self.__centralWidget)
        self.setGeometry(self.__windowStartPositionX, self.__windowStartPositionY, self.__windowWidth, self.__windowHeight)
        self.setWindowTitle(self.__programTitle)

        self.__sendButton = QtWidgets.QPushButton("Update Peer List", self)
        self.__sendButton.clicked.connect(lambda: self.__send(json.dumps({"type": "Request Update", "data": self.__accountID}), self.__accountWiseLedgerDNS))

        # Manage the layout
        mainLayout = QtWidgets.QGridLayout()
        mainLayout.addWidget(self.__sendButton, 0, 0)

        self.__centralWidget.setLayout(mainLayout)
        self.show()

        # Create Main Frame
        # first join the network, initialization
        # create new AccountWiseLedger class for me
        # retrieve others AccountWiseLedgers from the network
        # retrieve the address table for every member in the network

    def __getHostnameIP(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return None

    def __send(self, outputMsg, ipPortTuple):
        self.__socket.sendto(outputMsg.encode(), ipPortTuple)
        return

    def __listen(self, inputMsg):

        if inputMsg["type"] == "TEST":
            print("Just a test msg")
        elif inputMsg["type"] == "DNS update":
            self.__accountWiseLedgerList = inputMsg["data"]
            print(self.__accountWiseLedgerList)


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


app = Flask(__name__)


@app.route("/transactions/new/", methods=["POST"])
def newTransaction():
    # create new transaction task for me, broadcast the task to everyone and wait for a new high council to solve it.
    task = request.get_json()
    required = ["senderID", "receiverID", "amount"]
    if not all(k in task for k in required):
        return 'Missing values', 400

    print("Someone Called New Transactions", task)
    return "New Transaction" + str(task)


@app.route("/mine", methods=["GET"])
def incommingTask():
    # election, mining, share results to high council members, share result to everyone in the network
    print("Someone Called Mine")
    return "Mine"


def flaskMain():
    parser = ArgumentParser()
    parser.add_argument("-H", "--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", default=5000, type=int)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=True)


def guiMain():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # flaskMain()
    guiMain()
