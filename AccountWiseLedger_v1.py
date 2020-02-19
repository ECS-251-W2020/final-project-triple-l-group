#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 21:59:10 2020

@author: root
"""

from Blockchain import Blockchain
from flask import Flask
from argparse import ArgumentParser
import socket

app = Flask(__name__)
class AccountWiseLedger(object):

    def __init__(self, ownerID, address):
        self.__ownerID = ownerID
        self.__address = address
        self.__powDifficulty = 5
        self.__transactionChain = Blockchain(self.__ownerID, self.__powDifficulty)
    
    
    def sendRequest(self, target_address):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('target_address', 50000))
        s.listen(1)
        conn, addr = s.accept()
        while 1:
            data = conn.recv(1024)
            if not data:
                break
            conn.sendall(data)
        conn.close()
        
    def receiveResult(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', 50000))
        s.sendall('Hello, world')
        data = s.recv(1024)
        s.close()
        print('Received', repr(data))


def testAccount():
    account = AccountWiseLedger("testAccount", "127.0.0.1:5001")
    account.sendRequest()
         
if __name__ == '__main__':
    
    parser = ArgumentParser()
    parser.add_argument('-H', '--host', default='127.0.0.1')
    parser.add_argument('-p', '--port', default=5001, type=int)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=True)
