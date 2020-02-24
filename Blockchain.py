import hashlib
import json
from time import time


class Blockchain(object):

    def __init__(self, ownerID, powDifficulty):
        self.__ownerID = ownerID
        self.__powDifficulty = powDifficulty
        self.__balance = 0
        self.__chain = [{
            "taskID": None,
            "memo": "Chain Head",
            "preHash": None
        }]

    def __len__(self):
        return len(self.__chain)

    def __str__(self):
        ans = "<---------START CHAIN--------->\n"
        for block in self.__chain:
            ans += str(block) + ":" + self.hash256(block) + "\n"
        return ans + "<----------END CHAIN---------->"

    def append(self, block):
        if self.validBlock(block, self.__powDifficulty) and block["preHash"] == self.hash256(self.lastBlock) and (block["senderID"] == self.ownerID or block["receiverID"] == self.ownerID):
            self.__chain.append(block)
            if block["senderID"] == self.__ownerID:
                self.__balance -= block["amount"]
            elif block["receiverID"] == self.__ownerID:
                self.__balance += block["amount"]
            return True
        else:
            return False

    @property
    def ownerID(self):
        return self.__ownerID

    @property
    def lastBlock(self):
        return self.__chain[-1]

    @property
    def balance(self):
        return self.__balance

    @staticmethod
    def createNewBlock(powDifficulty, taskID, senderID, receiverID, amount, preHash):
        block = {
            "taskID": taskID,
            "timestamp": time(),
            "senderID": senderID,
            "receiverID": receiverID,
            "amount": amount,
            "nonce": 0,
            "preHash": preHash
        }

        powThreshold = "0" * powDifficulty
        while Blockchain.hash256(block)[:powDifficulty] != powThreshold:
            block["nonce"] += 1

        return block

    @staticmethod
    def validBlock(block, powDifficulty):
        return Blockchain.hash256(block)[:powDifficulty] == "0" * powDifficulty

    @staticmethod
    def hash256(block):
        block_string = json.dumps(block).encode()
        return hashlib.sha256(block_string).hexdigest()


def unitTest():
    testDifficulty = 4
    testChain = Blockchain("testSender", testDifficulty)
    testBlock = Blockchain.createNewBlock(testDifficulty, len(testChain), "testSender", "testReceiver", 500, Blockchain.hash256(testChain.lastBlock))
    testChain.append(testBlock)
    testBlock = Blockchain.createNewBlock(testDifficulty, len(testChain), "testReceiver", "testSender", 1500, Blockchain.hash256(testChain.lastBlock))
    testChain.append(testBlock)
    testBlock = Blockchain.createNewBlock(testDifficulty, len(testChain), "testReceiver", "testSender", 3500, Blockchain.hash256(testChain.lastBlock))
    testChain.append(testBlock)
    print(testChain, testChain.balance)


if __name__ == "__main__":
    unitTest()
