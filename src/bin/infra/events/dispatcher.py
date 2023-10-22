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
    # _toListen: int

    def __init__(self, name, port ): #, toListen=True, listenNumber=1):
        self._name = name
        self._port = port
        # self._toListen = toListen
        # self._listenNum = listenNumber
        self._send = True

    def getName(self):
        return self._name

    def getPort(self):
        return self._port

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connecting with Server
        logger.info("#Connecting Dispatcher: %s:%s", self._name, self._port)
        self._sock.connect((self._host, self._port))
        self._connected = True
        # if self._toListen == True:
        #     self._sock.listen(self._listenNum)

    def sendDataPack(self, packet):
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
            self.addSleep()
            # self.connect()
            # self.sendDataPack(packet)

    def close(self):
        self._connected = False
        self._sock.close()

    def toSend(self):
        return self._send

    def setSend(self, yes: bool):
        self._send = yes

    def addSleep(self, milliseconds=25):
        '''
        this is done because the socket fails when high amount of data is sent at fast speed
        '''
        time.sleep(milliseconds / 1000)

"""

def main():
    # host = '127.0.0.1'  # Listen on all available interfaces
    port = 8000
    dispatcher = Dispatcher("SCS", port)
    dispatcher.connect()
    instId = 1
    file = input_file

    with open(file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            need = row[0]
            need = re.sub("\s+", delim, need.strip())
            entry = list(need.split(delim))
            tickTime = datetime.datetime.fromtimestamp(int(entry[0])/1e9)
            tickSize = Decimal('0.01') if str(entry[3]) == 'SCH' else Decimal('0.001')
            tr = TickRead(tickTime, int(entry[1]), str(entry[2]), str(entry[3]), str(entry[4]), Decimal(str(entry[5])), int(entry[6]), instId, tickSize)
            try:
                # while True:
                #     # response = str(dispatcher._sock.recv(1024).decode())
                #     # print(response)
                #     # print(dispatcher._sock.getsockname())
                #     if response == "Hold"+dispatcher.getName():
                #         dispatcher.setSend(False)
                #     else:
                #         dispatcher.setSend(True)
                dispatcher.addSleep()
                dispatcher.sendDataPack(tr)
                # break

            except KeyboardInterrupt:
                dispatcher.close()
                logger.warning("Dispatcher closed, by keyboard interruption")

        logger.info("Dispatcher:%s has read all ticks. Closing now...", dispatcher.getName())
        dispatcher.sendDataPack("CLOSED")
        # Listener will close once its work is done, no need to tell when to close the listener
        dispatcher.close()

"""