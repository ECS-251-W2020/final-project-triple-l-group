from Blockchain import Blockchain


class AccountWiseLedger(object):

    def __init__(self, ownerID, address):
        self.__ownerID = ownerID
        self.__address = address
        self.__powDifficulty = 4
        self.__transactionTask = {}
        self.__transactionBalance = 0
        self.__blockchain = Blockchain(self.__ownerID, self.__powDifficulty)

    def __str__(self):
        return str(self.__blockchain)

    def newTransaction(self, task):
        if (task["senderID"] == self.__ownerID and task["amount"] <= (self.__blockchain.balance + self.__transactionBalance)) or task["receiverID"] == self.__ownerID:
            self.__transactionTask[Blockchain.hash256(task)] = task
            self.__transactionBalance += task["amount"] if task["receiverID"] == self.__ownerID else -task["amount"]
            return True
        else:
            return False

    def createNewBlock(self, task):
        return Blockchain.createNewBlock(self.__powDifficulty, Blockchain.hash256(task), task["senderID"], task["receiverID"], task["amount"], Blockchain.hash256(self.__blockchain.lastBlock))

    def receiveResult(self, block):
        if self.__transactionTask[block["taskID"]]["senderID"] == block["senderID"] and self.__transactionTask[block["taskID"]]["receiverID"] == block["receiverID"] and self.__transactionTask[block["taskID"]]["amount"] == block["amount"]:
            appendResult = self.__blockchain.append(block)
            if appendResult:
                del self.__transactionTask[block["taskID"]]
                self.__transactionBalance += block["amount"] if block["senderID"] == self.__ownerID else -block["amount"]
                return True
        return False

    @property
    def ownerID(self):
        return self.__ownerID

    @property
    def address(self):
        return self.__address

    @property
    def actualBalance(self):
        return self.__blockchain.balance

    @property
    def pendingBalance(self):
        return self.__transactionBalance


def unitTest():
    testAccount = AccountWiseLedger("917796371", "A")
    testTask = {
        "senderID": "testSender",
        "receiverID": "917796371",
        "amount": 1500
    }

    print("New Transaction Creation: ", testAccount.newTransaction(testTask))
    print("Actual vs Pending Balance: ", testAccount.actualBalance, testAccount.pendingBalance)
    testBlock = testAccount.createNewBlock(testTask)
    print("Block Append:", testAccount.receiveResult(testBlock))
    print(testAccount, testAccount.actualBalance, testAccount.pendingBalance)

    testTask = {
        "senderID": "917796371",
        "receiverID": "testReceiver",
        "amount": 500
    }

    print("New Transaction Creation: ", testAccount.newTransaction(testTask))
    print("Actual vs Pending Balance: ", testAccount.actualBalance, testAccount.pendingBalance)
    testBlock = testAccount.createNewBlock(testTask)
    print("Block Append:", testAccount.receiveResult(testBlock))
    print(testAccount, testAccount.actualBalance, testAccount.pendingBalance)

    return


if __name__ == "__main__":
    unitTest()
