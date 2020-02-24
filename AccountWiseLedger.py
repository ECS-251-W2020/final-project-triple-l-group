from Blockchain import Blockchain


class AccountWiseLedger(object):

    def __init__(self, ownerID, address):
        self.__ownerID = ownerID
        self.__address = address
        self.__powDifficulty = 4
        self.__transactionTask = {}
        self.__blockchain = Blockchain(self.__ownerID, self.__powDifficulty)

    def __str__(self):
        return str(self.__blockchain)

    def newTransaction(self, task):
        if (task["senderID"] == self.__ownerID and task["amount"] <= self.__blockchain.balance) or task["receiverID"] == self.__ownerID:
            self.__transactionTask[task["index"]] = task
            return True
        else:
            return False

    def createNewBlock(self, senderID, receiverID, amount):
        return Blockchain.createNewBlock(self.__powDifficulty, len(self.__blockchain), senderID, receiverID, amount, Blockchain.hash256(self.__blockchain.lastBlock))

    def receiveResult(self, block):
        if self.__transactionTask[block["index"]]["senderID"] == block["senderID"] and self.__transactionTask[block["index"]]["receiverID"] == block["receiverID"] and self.__transactionTask[block["index"]]["amount"] == block["amount"]:
            appendResult = self.__blockchain.append(block)
            if appendResult:
                del self.__transactionTask[block["index"]]
                return True
        return False

    @property
    def ownerID(self):
        return self.__ownerID

    @property
    def address(self):
        return self.__address

    @property
    def balance(self):
        return self.__blockchain.balance


def unitTest():
    testAccount = AccountWiseLedger("917796371", "A")
    testTask = {
        "index": 1,
        "senderID": "testSender",
        "receiverID": "917796371",
        "amount": 1500
    }

    print("New Transaction Creation: ", testAccount.newTransaction(testTask))
    testBlock = testAccount.createNewBlock("testSender", "917796371", 1500)
    print("Block Append:", testAccount.receiveResult(testBlock))
    print(testAccount, testAccount.balance)

    testTask = {
        "index": 2,
        "senderID": "917796371",
        "receiverID": "testReceiver",
        "amount": 500
    }

    print("New Transaction Creation: ", testAccount.newTransaction(testTask))
    testBlock = testAccount.createNewBlock("917796371", "testReceiver", 500)
    print("Block Append:", testAccount.receiveResult(testBlock))
    print(testAccount, testAccount.balance)

    return


if __name__ == "__main__":
    unitTest()
