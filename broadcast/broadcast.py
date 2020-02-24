import socket
import json

# sender and receiver encode and decode data, address, respectively
def send_encode(socket, tar_addr, data ):
    socket.sendto(data.encode(),(tar_addr[0],tar_addr[1]))

def rec_decode(socket):
    data, sou_addr = socket.recvfrom(1024)
    return data.decode(), sou_addr

# send data, received data, and broadcast
def send_data(socket,tar_addr,data):    
    send_encode(socket,tar_addr,json.dumps(data))

def broadcast(socket,data, nodes):
    for n in nodes.values():
        send_data(socket,n,data)

def rec_data(socket):
    while 1:
        data,sou_addr = rec_decode(socket)
        print(data)
