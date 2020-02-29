import hashlib
import json
from time import time


class Blockchain(object):

    def __init__(self, ownerID, powDifficulty, balance=1000, chain=None):
        self.__ownerID = ownerID
        self.__powDifficulty = powDifficulty
        self.__balance = balance

        if chain is None:
            self.__chain = [{
                "taskID": "None",
                "memo": "Chain Head",
                "amount": 1000,
                "preHash": "None"
            }]
        else:
            self.__chain = chain

    @classmethod
    def createByJsonBytes(cls, inputStr):
        input = json.loads(inputStr)
        return cls(input["ownerID"], input["powDifficulty"], input["balance"], input["chain"])

    def __len__(self):
        return len(self.__chain)

    def __str__(self):
        ans = {"ownerID": self.__ownerID, "powDifficulty": self.__powDifficulty, "balance": self.__balance, "chain": self.__chain}
        return str(ans).replace("\'", "\"")

    def append(self, block):
        if self.validBlock(block, self.__powDifficulty) and block["preHash"] == self.hash256(self.viewLastBlock) and (block["senderID"] == self.viewOwnerID or block["receiverID"] == self.viewOwnerID):
            self.__chain.append(block)
            if block["senderID"] == self.__ownerID:
                self.__balance -= block["amount"]
            elif block["receiverID"] == self.__ownerID:
                self.__balance += block["amount"]
            return True
        else:
            return False

    @property
    def viewOwnerID(self):
        return self.__ownerID

    @property
    def viewLastBlock(self):
        return self.__chain[-1]

    @property
    def viewBalance(self):
        return self.__balance

    @property
    def outputDict(self):
        return {"ownerID": self.__ownerID, "powDifficulty": self.__powDifficulty, "balance": self.__balance, "chain": self.__chain}

    @property
    def outputJsonBytes(self):
        return json.dumps(self.outputDict).encode()

    @staticmethod
    def createNewBlock(powDifficulty, taskID, senderID, receiverID, amount, preHash, taskAbortSignal=False):
        block = {
            "taskID": taskID,
            "timestamp": time(),
            "senderID": senderID,
            "receiverID": receiverID,
            "amount": amount,
            "msg": "None",
            "nonce": 0,
            "preHash": preHash
        }

        if taskAbortSignal:
            block["msg"] = "Task Abort"

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


def __unitTest():
    testDifficulty = 4
    testChain = Blockchain("testSender", testDifficulty)
    testBlock = Blockchain.createNewBlock(testDifficulty, len(testChain), "testSender", "testReceiver", 500, Blockchain.hash256(testChain.viewLastBlock))
    testChain.append(testBlock)
    testBlock = Blockchain.createNewBlock(testDifficulty, len(testChain), "testReceiver", "testSender", 1500, Blockchain.hash256(testChain.viewLastBlock))
    testChain.append(testBlock)
    testBlock = Blockchain.createNewBlock(testDifficulty, len(testChain), "testReceiver", "testSender", 3500, Blockchain.hash256(testChain.viewLastBlock))
    testChain.append(testBlock)

    print(testChain)
    print(Blockchain.createByJsonBytes(json.dumps(testChain.outputDict)))


if __name__ == "__main__":
    __unitTest()
