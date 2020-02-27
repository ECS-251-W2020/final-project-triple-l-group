import threading
import socket
import sys
import json
import time
import broadcast as bd


class Node:
    ip = ("127.0.0.1", 8891)
    nodes = {}
    myid = ""
    socket = {}

    def process(self):
        while 1:
            data, addr = bd.rec_decode(self.socket)
            action = json.loads(data)
            if action['type'] == 'newpeer':
                print("A new node is added")
                self.nodes[action['data']] = addr
                # print(addr)
                bd.send_data(self.socket, addr, {
                    "type": 'peers',
                    "data": self.nodes
                })

            if action['type'] == 'peers':
                print("Received a bunch of nodes")
                self.nodes.update(action['data'])
                # introduce youself. 
                bd.broadcast(self.socket, {
                    "type": "introduce",
                    "data": self.myid
                }, self.nodes)

            if action['type'] == 'introduce':
                print("Get a new node.")
                self.nodes[action['data']] = addr

            if action['type'] == 'input':
                print(action['data'])

            if action['type'] == 'exit':
                if (self.myid == action['data']):
                    time.sleep(0.5)
                    break
                value, key = self.nodes.pop(action['data'])
                print(action['data'] + " is left.")

    def startnode(self):
        bd.send_data(self.socket, self.ip, {
            "type": "newpeer",
            "data": self.myid
        })

    def send(self):
        while 1:
            msg_input = input("$:")
            if msg_input == "exit":
                bd.broadcast(self.socket, {
                    "type": "exit",
                    "data": self.myid
                }, self.nodes)
                break
            if msg_input == "all_nodes":
                print(self.nodes)
                continue
            l = msg_input.split()
            if l[-1] in self.nodes.keys():
                tar_addr = self.nodes[l[-1]]
                d = ' '.join(l[:-1])
                bd.send_data(self.socket, tar_addr, {
                    "type": "input",
                    "data": d
                })
            else:
                bd.broadcast(self.socket, {
                    "type": "input",
                    "data": msg_input
                }, self.nodes)
                continue


def main():
    port = int(sys.argv[1])
    sour_addr = ("127.0.0.1", port)
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    st.bind((sour_addr[0], sour_addr[1]))
    node = Node()
    node.myid = sys.argv[2]
    node.socket = st
    node.startnode()
    thread1 = threading.Thread(target=node.process, args=())
    thread2 = threading.Thread(target=node.send, args=())

    thread1.start()
    thread2.start()


if __name__ == '__main__':
    main()
