from src.bin.markets.tbt_datafeed.processor import *
from src.bin.markets.tbt_datafeed.messages import *
from src.bin.markets.oms.messages import *
from src.bin.markets.tbt_datafeed.tick_print_orderbook import *
import src.config.logger as log
from src.bin.infra.events.listener import *
logger = log.logger


class TickDispatcher(object):
    tbtProcessor: TbtProcessor
    _allRawTicks: [TickRead]

    def __init__(self, tlisten: TickListener, tbtProc: TbtProcessor):
        self.tbtProcessor = tbtProc
        self.listener = tlisten
        self.instId = tbtProc.getInstrumentId()

    def beginEvents(self):
            self.listener.start()
            self.listener.addProcessDelegate(self.tbtProcessor.readEvent)
            self.listener.listen()
