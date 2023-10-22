'''First start the listener and then start the reader to connect to it'''

import socket
import pickle
import time
import src.config.logger as log
logger = log.logger

class Dispatcher:
    _name: str
    _host = '127.0.0.1'
    _port: int
    _connected = False

    def __init__(self, name, port ):
        self._name = name
        self._port = port
        self._send = True

    def getName(self):
        return self._name

    def getPort(self):
        return self._port

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.info("#Connecting Dispatcher: %s:%s", self._name, self._port)
        self._sock.connect((self._host, self._port))
        self._connected = True

    def sendDataPack(self, packet):
        assert self._send
        if not self._connected:
            self.connect()
        try:
            if not packet:
                logger.warn("%s Nothing to dispatch, no data received.", self._name)
            else:
                pickledData = pickle.dumps(packet)
                self._sock.send(pickledData)
        except:
            logger.warning("Packet sending not working. Sleeping for some time...")
            self.addSleep(10)

    def close(self):
        self._connected = False
        self._sock.close()

    def toSend(self):
        return self._send

    def setSend(self, yes: bool):
        self._send = yes

    def addSleep(self, milliseconds=0):
        '''
        this is done because the socket fails when high amount of data is sent at fast speed.
        Currently no sleeping is required, hence kept it to be zero
        '''
        time.sleep(milliseconds / 1000)
