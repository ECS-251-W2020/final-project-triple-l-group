from Blockchain import Blockchain


class AccountWiseLedger(object):

    def __init__(self, ownerID, address):
        self.__ownerID = ownerID
        self.__address = address
        self.__powDifficulty = 5
        self.__transactionChain = Blockchain(self.__ownerID, self.__powDifficulty)

    def sendRequest(self):
        return

    def receiveResult(self):
        return