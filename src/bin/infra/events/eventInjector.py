import re
import csv
from src.bin.markets.tbt_datafeed.messages import *
from decimal import Decimal
from src.config.data_cfg import delim
from src.bin.infra.events.dispatcher import *
import src.config.logger as log
logger = log.logger

class EventInject(object):
    _dispatcher: Dispatcher
    _file: str
    _instId: int
    _fileToRead: str
    _tradable: Tradable

    def __init__(self, port, tdb: Tradable, fileToRead):
        self._dispatcher = Dispatcher(tdb.tickerName, port)
        self._tradable = tdb
        self._fileToRead = fileToRead

    def startInjection(self):
        self._dispatcher.connect()
        response = None
        with open(self._fileToRead, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                need = row[0]
                need = re.sub("\s+", delim, need.strip())
                entry = list(need.split(delim))
                tickTime = datetime.datetime.fromtimestamp(int(entry[0]) / 1e9)
                tr = TickRead(tickTime, int(entry[1]), str(entry[2]), str(entry[3]), str(entry[4]),
                              Decimal(str(entry[5])), int(entry[6]), self._tradable.instrumentId, self._tradable.tickSize)
                try:
                    while True:
                        if response == "Hold"+self._tradable.tickerName:
                            self._dispatcher.setSend(False)
                            self._dispatcher.addSleep()
                            response = str(self._dispatcher._sock.recv(1024).decode())
                        else:
                            self._dispatcher.setSend(True)
                            self._dispatcher.sendDataPack(tr)
                            self._dispatcher.addSleep()
                            response = str(self._dispatcher._sock.recv(1024).decode())
                            break

                except KeyboardInterrupt:
                    self._dispatcher.close()
                    logger.warning("Dispatcher closed, by keyboard interruption")

            logger.info("Dispatcher:%s has read all ticks. Closing now...", self._dispatcher.getName())
            self._dispatcher.sendDataPack("CLOSED")
            '''Listener will close once its work is done, no need to tell when to close the listener'''
            self._dispatcher.close()

    def shutDown(self):
        self._dispatcher.close()

