# first start the listener and then start the dispatcher to connect to it
# broadcasts to clients

import re
import csv
import socket
import pickle
import threading
from src.bin.markets.tbt_datafeed.messages import *
from decimal import Decimal
from src.config.data_cfg import input_file, delim
import src.config.logger as log
logger = log.logger

class TickListener:
    _name: str
    _host = '127.0.0.1'
    _port: int
    _connected = False
    # _toListen: int
    _totalClient: int
    _connections = []
    _tick1: TickRead
    _tick2: TickRead

    def __init__(self, name, port, processData, numToListen=1):
        self._name = name
        self._port = port
        self._totalClient = numToListen
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self._clients_lock = threading.Lock()
        self.processData = processData

    def processTick(self, tick):
        logger.info("#GOT:%s %s", tick.basicTickerName, tick)

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self._host, self._port))
        self.server_socket.listen(self._totalClient)  # Listen for up to 5 incoming connections
        logger.info("Server listening on %s:%s", self._host, self._port)
        for i in range(self._totalClient):
            conn, addr = self.server_socket.accept()
            self._connections.append(conn)

    def listen(self):
        first = True
        while True:
            try:
                if len(self._connections) == 2:
                    if first:
                        self._tick1 = pickle.loads(self._connections[0].recv(4096))
                        self._tick2 = pickle.loads(self._connections[1].recv(4096))
                        first = False

                    if not self._tick1:
                        # self._connections[0].close()
                        self.processTick(self._tick2)
                        self._tick2 = pickle.loads(self._connections[0].recv(4096))
                    elif not self._tick2:
                        # self._connections[1].close()
                        self.processTick(self._tick1)
                        self._tick1 = pickle.loads(self._connections[0].recv(4096))
                    else:
                        if self._tick1.eventTime < self._tick2.eventTime:
                            toSent = "Hold"+ self._tick2.basicTickerName
                            self.server_socket.sendall(toSent.encode())
                            self.processTick(self._tick1)
                            self._tick1 = pickle.loads(self._connections[0].recv(4096))
                        else:
                            toSent = "Hold" + self._tick1.basicTickerName
                            self.server_socket.sendall(toSent.encode())
                            self.processTick(self._tick2)
                            self._tick2 = pickle.loads(self._connections[0].recv(4096))
                else:
                    assert len(self._connections) == 1
                    self._tick1 = pickle.loads(self._connections[0].recv(4096))
                    if not self._tick1:
                        self.server_socket.close()
                        break
                    self.processTick(self._tick2)
            except KeyboardInterrupt:
                self.server_socket.close()
                logger.warn("Listener closed, by keyboard interruption")

            self.server_socket.close()
            break
        return


def main():
    tListen = TickListener("Listener", 8888, None)
    tListen.start()
    tListen.listen()



if __name__ == "__main__":
    main()

