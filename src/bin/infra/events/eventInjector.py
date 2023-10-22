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
        with open(self._fileToRead, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                need = row[0]
                need = re.sub("\s+", delim, need.strip())
                entry = list(need.split(delim))
                tickTime = datetime.datetime.fromtimestamp(int(entry[0]) / 1e9)
                # tickSize = Decimal('0.01') if str(entry[3]) == 'SCH' else Decimal('0.001')
                tr = TickRead(tickTime, int(entry[1]), str(entry[2]), str(entry[3]), str(entry[4]),
                              Decimal(str(entry[5])), int(entry[6]), self._tradable.instrumentId, self._tradable.tickSize)
                try:
                    # while True:
                    #     # response = str(dispatcher._sock.recv(1024).decode())
                    #     # print(response)
                    #     # print(dispatcher._sock.getsockname())
                    #     if response == "Hold"+dispatcher.getName():
                    #         dispatcher.setSend(False)
                    #     else:
                    #         dispatcher.setSend(True)
                    self._dispatcher.addSleep()
                    self._dispatcher.sendDataPack(tr)
                    # break

                except KeyboardInterrupt:
                    self._dispatcher.close()
                    logger.warning("Dispatcher closed, by keyboard interruption")

            logger.info("Dispatcher:%s has read all ticks. Closing now...", self._dispatcher.getName())
            self._dispatcher.sendDataPack("CLOSED")
            # Listener will close once its work is done, no need to tell when to close the listener
            self._dispatcher.close()

    def shutDown(self):
        self._dispatcher.close()

