from AccountWiseLedger import AccountWiseLedger
from flask import Flask, request
from argparse import ArgumentParser
from urllib.parse import urlencode
from io import BytesIO
import pycurl
import json
import socket


class UserInterface(object):

    def __init__(self):

        self.__accountID = "AAA"
        self.__accountAddress = ""
        self.__accountWiseLedgerDNS = "http://127.0.0.1:5000/get_list/"

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.bind((self.__getHostnameIP(), 5000))

        self.__accountWiseLedgerList = json.loads(self.getFromURL(self.__accountWiseLedgerDNS + self.__accountID))

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


    def __send(self, data, ipAddress):
        return


    def __listen(self):
        while True:
            data, sourceAddress = self.__socket.recvfrom(1024)
            action = json.loads(data)

            print(sourceAddress)
            return


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
    window = UserInterface()
    return


if __name__ == "__main__":
    # flaskMain()
    guiMain()
