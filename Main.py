from AccountWiseLedger import AccountWiseLedger
from flask import Flask
from argparse import ArgumentParser

app = Flask(__name__)


def joinNetwork():
    accountID, accountAddress = "", ""
    accountWiseLedgerList = {}
    # first join the network, initialization
    # create new AccountWiseLedger class for me
    # retrieve others AccountWiseLedgers from the network
    # retrieve the address table for every member in the network
    return accountID, accountAddress, accountWiseLedgerList

@app.route("/transactions/new")
def newTransaction():
    # create new transaction task for me, broadcast the task to everyone and wait for a new high council to solve it.
    return

@app.route("/mine")
def incommingTask():
    # election, mining, share results to high council members, share result to everyone in the network
    return


def main():
    accountID, accountAddress, accountWiseLedgerList = joinNetwork()

    parser = ArgumentParser()
    parser.add_argument("-H", "--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", default=5001, type=int)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=True)
    return


if __name__ == "__main__":
    main()
