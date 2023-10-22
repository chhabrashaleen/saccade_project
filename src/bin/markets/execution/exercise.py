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

    def __init__(self, _book1: TickPrintOrderbook, _book2: TickPrintOrderbook):
        self.book1 = _book1
        self.book2 = _book2
        self.book1.addDispatch(self.hNew, self.hCan, self.hMod, self.hTrd)
        self.book2.addDispatch(self.hNew, self.hCan, self.hMod, self.hTrd)
        self.lastSnap = None
        self.trdPrintCounts = 1200

    def hNew(self, obs: OBStatus, newTick: TbtTickNewCan):
        self.new += 1

        if self.trd <= self.trdPrintCounts and self.lastSnap is not None:
            # logger.info(obs)
            # logger.info("#NEW:%s", newTick)
        # logger.info("new:%s",copy(obs))
        # if self.trd <= self.trdPrintCounts and self.lastSnap is not None:
            # logger.info(obs)
            # logger.info("lastSnap %s %s",self.lastSnap[1],self.lastSnap[0])
            # logger.info("#TRADE:%s", trdTick)
            logger.info("#NEW:%s", obs)
        self.lastSnap = (copy(obs), "new")

    def hCan(self, obs: OBStatus, canTick: TbtTickNewCan):
        self.can += 1

        if self.trd <= self.trdPrintCounts and self.lastSnap is not None:
            # logger.info(obs)
            # logger.info("lastSnap %s %s",self.lastSnap[1],self.lastSnap[0])
            # logger.info("#TRADE:%s", trdTick)
            logger.info("#CAN:%s", obs)
        self.lastSnap = (copy(obs), "can")

    def hMod(self, obs: OBStatus, modTick: TbtTickMod):
        self.mod += 1
        self.lastSnap = (copy(obs), "mod")

    def hTrd(self, obs: OBStatus, trdTick: TbtTickTrd):
        self.trd += 1
        if self.trd <= self.trdPrintCounts:
            logger.info("%s %s %s",self.trd, obs.header.instrumentId, trdTick)
            # logger.info("#POST_TRADE_OBS %s",obs)
        self.lastSnap = (copy(obs), "new")


def __main__():
    tdb1 = Tradable(InstrumentType.Equity, 1, "SCH", Decimal('0.01'), 1, True)
    tdb2 = Tradable(InstrumentType.Equity, 2, "SCS", Decimal('0.001'), 1, True)

    ic = InstrumentContainer()
    ic.addInstrument(tdb1)
    ic.addInstrument(tdb2)

    tbtProcessor = TbtProcessor(ic)

    orderbook1 = TickPrintOrderbook(tdb1, tbtProcessor)
    orderbook2 = TickPrintOrderbook(tdb2, tbtProcessor)

    obticks = InstOBTicks(orderbook1, orderbook2)

    listener = TickListener("myListener",2, 8000)
    tickDispatcher = TickDispatcher(listener, tbtProcessor)
    tickDispatcher.beginEvents()

    logger.info("newTicks:%s, canTicks:%s, modTicks:%s, trdTicks:%s",
                obticks.new, obticks.can, obticks.mod, obticks.trd)

if __name__ == '__main__':
    __main__()



