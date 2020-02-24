from AccountWiseLedger import AccountWiseLedger
from flask import Flask, request
from argparse import ArgumentParser


class LocalData(object):

    def __init__(self):

        self.__accountID = "AAA"
        self.__accountAddress = ""
        self.__accountWiseLedgerList = {"AAA": AccountWiseLedger("AAA", "A")}

        # Create Main Frame
        # first join the network, initialization
        # create new AccountWiseLedger class for me
        # retrieve others AccountWiseLedgers from the network
        # retrieve the address table for every member in the network

    def newTransaction(self, task):
        return self.__accountWiseLedgerList[self.__accountID].newTransaction(task)


app = Flask(__name__)
myLocalData = LocalData()


@app.route("/transactions/new/", methods=["POST"])
def newTransaction():
    # create new transaction task for me, broadcast the task to everyone and wait for a new high council to solve it.
    task = request.get_json()
    required = ["senderID", "receiverID", "amount"]
    if not all(k in task for k in required):
        return 'Missing values', 400

    print("Append New Transaction: ", myLocalData.newTransaction(task))
    print("Someone Called New Transactions", task)
    return "New Transaction" + str(task)


@app.route("/mine", methods=["GET"])
def incommingTask():
    # election, mining, share results to high council members, share result to everyone in the network
    print("Someone Called Mine")
    return "Mine"


def main():
    parser = ArgumentParser()
    parser.add_argument("-H", "--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", default=5000, type=int)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
