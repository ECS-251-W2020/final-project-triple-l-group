from AccountWiseLedger import AccountWiseLedger
from flask import Flask, request
from argparse import ArgumentParser

app = Flask(__name__)
DNSTable = {}


@app.route("/get_list/<myID>", methods=["GET"])
def get_my_ip(myID):
    DNSTable[myID] = request.remote_addr
    return DNSTable, 200


def flaskMain():
    parser = ArgumentParser()
    parser.add_argument("-H", "--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", default=5000, type=int)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    flaskMain()
