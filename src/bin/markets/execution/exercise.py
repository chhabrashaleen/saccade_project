from src.bin.markets.tbt_datafeed.tick_print_orderbook import *
from src.bin.markets.tbt_datafeed.tick_dispatcher import *
import src.config.read_data as reader
import src.config.logger as log
from copy import copy
logger = log.logger

class InstOBTicks:
    new = 0
    can = 0
    trd = 0
    mod = 0

    def __init__(self, _book: TickPrintOrderbook):
        self.book = _book
        self.tradable = self.book.instrument
        self.tickerName = self.book.instrument.tickerName
        self.book.addDispatch(self.hNew, self.hCan, self.hMod, self.hTrd)
        self.lastSnap = None
        self.trdPrintCounts = 20

    def hNew(self, obs: OBStatus, newTick: TbtTickNewCan):
        self.new += 1
        # if self.new == 100:
        #     # logger.info(obs)
        #     logger.info("#NEW:%s", newTick)
        # logger.info("new:%s",copy(obs))
        if self.trd <= self.trdPrintCounts and self.lastSnap is not None:
            # logger.info(obs)
            # logger.info("lastSnap %s %s",self.lastSnap[1],self.lastSnap[0])
            # logger.info("#TRADE:%s", trdTick)
            logger.info("#NEW_TICK: %s", obs)
        self.lastSnap = (copy(obs), "new")

    def hCan(self, obs: OBStatus, canTick: TbtTickNewCan):
        self.can += 1

        if self.trd <= self.trdPrintCounts and self.lastSnap is not None:
            # logger.info(obs)
            # logger.info("lastSnap %s %s",self.lastSnap[1],self.lastSnap[0])
            # logger.info("#TRADE:%s", trdTick)
            logger.info("#CAN_TICK: %s", obs)
        self.lastSnap = (copy(obs), "can")

    def hMod(self, obs: OBStatus, modTick: TbtTickMod):
        self.mod += 1
        self.lastSnap = (copy(obs), "mod")

    def hTrd(self, obs: OBStatus, trdTick: TbtTickTrd):
        self.trd += 1
        if self.trd <= self.trdPrintCounts:
            logger.info(trdTick)
            logger.info("#POST_TRADE_OBS %s",obs)
        self.lastSnap = (copy(obs), "new")


def __main__():
    # allTicks = reader.fetchTicks(file)
    tbtProcessor = TbtProcessor()
    omsProcessor = OmsProcessor()

    tdb = Tradable(InstrumentType.Equity, 1, "SCH", Decimal('0.001'), 1, True)
    orderbook = TickPrintOrderbook(tdb, tbtProcessor, omsProcessor)
    obticks = InstOBTicks(orderbook)
    # orderbook.addDispatch(obticks.hNew, obticks.hCan, obticks.hMod, obticks.hTrd)

    tickDispatcher = TickDispatcher(reader.fetchTicks, tbtProcessor)
    tickDispatcher.beginEvents()

    logger.info("newTicks:%s, canTicks:%s, modTicks:%s, trdTicks:%s",
                obticks.new, obticks.can, obticks.mod, obticks.trd)

if __name__ == '__main__':
    __main__()



