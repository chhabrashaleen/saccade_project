from src.bin.markets.tbt_datafeed.tick_print_orderbook import *
from src.bin.markets.tbt_datafeed.tick_dispatcher import *
# import src.config.read_data as reader
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
            logger.info("%s %s",self.trd,trdTick)
            logger.info("#POST_TRADE_OBS %s",obs)
        self.lastSnap = (copy(obs), "new")


def __main__():
    # allTicks = reader.fetchTicks(file)
    omsProcessor = OmsProcessor()
    listener = TickListener("listenEvents",2)

    tdb1 = Tradable(InstrumentType.Equity, 1, "SCH", Decimal('0.01'), 1, True)
    tdb2 = Tradable(InstrumentType.Equity, 2, "SCS", Decimal('0.001'), 1, True)

    tbtProcessor1 = TbtProcessor(tdb1.instrumentId)
    orderbook1 = TickPrintOrderbook(tdb1, tbtProcessor1, omsProcessor)
    obticks1 = InstOBTicks(orderbook1)
    # orderbook.addDispatch(obticks.hNew, obticks.hCan, obticks.hMod, obticks.hTrd)

    tbtProcessor2 = TbtProcessor(tdb2.instrumentId)
    orderbook2 = TickPrintOrderbook(tdb2, tbtProcessor2, omsProcessor)
    obticks2 = InstOBTicks(orderbook2)

    tickDispatcher = TickDispatcher(listener, tbtProcessor2)
    # tickDispatcher = TickDispatcher(listener, tbtProcessor1)
    tickDispatcher.beginEvents()

    logger.info("newTicks:%s, canTicks:%s, modTicks:%s, trdTicks:%s",
                obticks2.new, obticks2.can, obticks2.mod, obticks2.trd)

if __name__ == '__main__':
    __main__()



