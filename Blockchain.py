import hashlib
import json
from time import time


class Blockchain(object):

    def __init__(self, ownerID, powDifficulty):
        self.__ownerID = ownerID
        self.__powDifficulty = powDifficulty
        self.__chain = [{
            "index": 0,
            "timestamp": 0,
            "senderID": None,
            "receiverID": None,
            "amount": 0,
            "nonce": 0,
            "preHash": 0
        }]

    def __len__(self):
        return len(self.__chain)

    def append(self, block):
        if self.hash256(block)[:self.__powDifficulty] == "0" * self.__powDifficulty and block["preHash"] == self.hash256(self.lastBlock) and (block["senderID"] == self.ownerID or block["receiverID"] == self.ownerID):
            self.__chain.append(block)
            return True
        else:
            return False

    @property
    def ownerID(self):
        return self.__ownerID

    @property
    def lastBlock(self):
        return self.__chain[-1]

    @staticmethod
    def createNewBlock(powDifficulty, index, senderID, receiverID, amount, preHash):
        block = {
            "index": index,
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
    def hash256(block):
        block_string = json.dumps(block).encode()
        return hashlib.sha256(block_string).hexdigest()


def unitTest():
    testDifficulty = 5
    testChain = Blockchain("testSender", testDifficulty)
    testBlock = Blockchain.createNewBlock(testDifficulty, len(testChain), "testSender", "testReceiver", 500, Blockchain.hash256(testChain.lastBlock))
    testChain.append(testBlock)
    print(testChain.ownerID, testChain.lastBlock, Blockchain.hash256(testChain.lastBlock))
    print(testChain)


if __name__ == "__main__":
    unitTest()
