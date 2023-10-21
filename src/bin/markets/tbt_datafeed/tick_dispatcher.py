from src.bin.markets.tbt_datafeed.processor import *
from src.bin.markets.tbt_datafeed.messages import *
from src.bin.markets.oms.messages import *
from src.bin.markets.tbt_datafeed.tick_print_orderbook import *
import src.config.logger as log
logger = log.logger


class TickDispatcher(object):
    tbtProcessor: TbtProcessor
    _allRawTicks: [TickRead]

    def __init__(self, fetchTickFn, tbtProc: TbtProcessor):
        self.tbtProcessor = tbtProc
        self.fetchTickFn = fetchTickFn
        self.instId = tbtProc.getInstrumentId()

    def beginEvents(self):
        self._allRawTicks = self.fetchTickFn(self.instId)
        for tick in self._allRawTicks:
            self.tbtProcessor.readEvent(tick)
