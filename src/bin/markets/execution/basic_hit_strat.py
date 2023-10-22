# This module is a basic hit execution strategy using the designed framework

from src.bin.markets.oms.oms import *
from src.bin.markets.execution.messages import *
# from src.bin.markets.oms.processor import *
from src.bin.markets.tbt_datafeed.tick_print_orderbook import *
from src.bin.markets.tbt_datafeed.tick_dispatcher import *
from src.bin.markets.oms.rms import *
from src.bin.markets.pnl import *
from datetime import timedelta
from copy import copy
import src.config.logger as log
logger = log.logger


class HiLo:
    maxPrice = Decimal(-sys.maxsize)
    minPrice = Decimal(sys.maxsize)
    _lastEntryTime = datetime.datetime.min
    '''
    price checked every 5 seconds, and total time of array will be 300 seconds
    hence we will have moving hi lo of last 5 minutes
    Therefore array size will remain 60
    '''
    _gap = datetime.timedelta(seconds=5)
    _prices = []

    def addEntry(self, p, eventTime):
        if eventTime - self._lastEntryTime > self._gap:
            self._prices.append(p)
            self.maxPrice = max(self._prices)
            self.minPrice = min(self._prices)
            self._lastEntryTime = eventTime

        if len(self._prices) > 60:
            assert len(self._prices) == 61
            self._prices = self._prices[1:61]


class HitStrategy(ExecutionStrategy):

    _oid: Order
    _quitExecution: bool
    _remainingFillQty: int

    _listener: TickListener
    _tickDispatcher: TickDispatcher
    _tbtProcessor: TbtProcessor

    _sch: Tradable
    _schRC: RmsCoordinator
    _schOB: TickPrintOrderbook
    _schOBS: OBStatus
    _schOMS: OrderManager
    # _schProc: OmsProcessor
    _schPnl: Pnl
    _schBuyTCost = Decimal('0.001')
    _schSellTCost = Decimal('0.002')
    _schHiLo = HiLo()

    _scs: Tradable
    _scsRC: RmsCoordinator
    _scsOB: TickPrintOrderbook
    _scsOBS: OBStatus
    _scsOMS: OrderManager
    # _scsProc: OmsProcessor
    _scsPnl: Pnl
    _scsBuyTCost = Decimal('0.001')
    _scsSellTCost = Decimal('0.002')
    _scsHiLo = HiLo()

    _bpsMargin: int
    _stratPort: int

    _lastUpdateTime: datetime.datetime
    _timeBetweenTrades = timedelta(seconds=10)
    _schLastTradeTime = datetime.datetime.min
    _scsLastTradeTime = datetime.datetime.min

    _startTime = None
    _tradeStartDiff = timedelta(seconds=30)

    '''
    I haven't set the RmsCoordinator quantity risk limits into this strategy, 
    can be done very easily in the constructor or any function.
    '''
    def __init__(self, sch: Tradable, scs: Tradable, tbtProcessor: TbtProcessor,
                 schOB: TickPrintOrderbook, scsOB: TickPrintOrderbook,
                 schRms: RmsCoordinator, scsRms: RmsCoordinator,
                 schPort: int, scsPort: int,
                 stratPort: int
                 ):

        self._sch = sch
        self._schOB = schOB
        self._schRC = schRms
        self._schDispatcher = Dispatcher("OrderSendSCH", schPort)
        # self._schProc = OmsProcessor(self._sch, self._schDispatcher, 1, 1, "SCH_OMS")
        self._schOMS = OrderManager(self._sch, self._schRC, 1, 1, "SCH_OMS", self._schDispatcher)
        self._schPnl = Pnl(sch.tickerName, self._schBuyTCost, self._schSellTCost)

        self._scs = scs
        self._scsOB = scsOB
        self._scsRC = scsRms
        self._scsDispatcher = Dispatcher("OrderSendSCS", scsPort)
        # self._scsProc = OmsProcessor(self._scs, self._scsDispatcher, 2, 2, "SCS_OMS")
        self._scsOMS = OrderManager(self._scs, self._scsRC, 2, 2, "SCS_OMS", self._scsDispatcher)
        self._scsPnl = Pnl(scs.tickerName, self._scsBuyTCost, self._scsSellTCost)

        ic = InstrumentContainer()
        ic.addInstrument(self._sch)
        ic.addInstrument(self._scs)
        self._tbtProcessor = tbtProcessor

        self._stratPort = stratPort
        self._listener = TickListener("HitListener", totalClient=2, port=self._stratPort)
        self._tickDispatcher = TickDispatcher(self._listener, self._tbtProcessor)

        self._schOB.addDispatch(self.hTick, self.hCan, None, self.hTick)
        self._scsOB.addDispatch(self.hTick, self.hCan, None, self.hTick)

        self._schOMS.addEventListeners(self.hConfNew, None, None, self.hFill, self.hFinished)
        self._scsOMS.addEventListeners(self.hConfNew, None, None, self.hFill, self.hFinished)


    def canTrade(self):
        elapsedTime = self._lastUpdateTime - self._startTime
        return True if elapsedTime > self._tradeStartDiff else False

    def updateSCHRms(self, p):
        self._schRC.updateBuyMinMaxPrice(p*6/10, p*14/10)
        self._schRC.updateSellMinMaxPrice(p*6/10, p*14/10)

    def updateSCSRms(self, p):
        self._scsRC.updateBuyMinMaxPrice(p*6/10, p*14/10)
        self._scsRC.updateSellMinMaxPrice(p*6/10, p*14/10)

    def tradeSCH(self, p, q):
        if not self.canTrade():
            return

        logger.info("Strategy sending new order at:%s", self._schOBS)
        order = self._schOMS.orderNew(self._schOBS, p, q, self._lastUpdateTime)

        if order.orderNumber == 0:
            '''The new order was not successful'''
            return

        '''Here: The new order got placed'''
        logger.info("Strategy processing exchange msg:%s", self._schOMS.tradable)
        self._schOMS.processExchangeMsg()
        '''This will call hConfNew'''
        '''If a Fill happened, this will also call hFill'''

    def tradeSCS(self, p, q):
        if not self.canTrade():
            return

        logger.info("Strategy sending new order at:%s", self._scsOBS)
        order = self._scsOMS.orderNew(self._scsOBS, p, q, self._lastUpdateTime)

        if order.orderNumber == 0:
            '''The new order was not successful'''
            return

        '''Here: The new order got placed'''
        logger.info("Strategy processing exchange msg:%s", self._scsOMS.tradable)
        self._scsOMS.processExchangeMsg()
        '''This will call hConfNew'''
        '''If a Fill happened, this will also call hFill'''

    def hTick(self, obs: OBStatus, tick):

        obs = copy(obs)
        if self._startTime is None:
            self._startTime = obs.header.eventTime
        self._lastUpdateTime = obs.header.eventTime
        midPrice = (obs.bestBid + obs.bestAsk)/2

        if obs.header.instrumentId == self._sch.instrumentId:
            '''updating Rms buyMin buyMax and sellMin sellMax prices'''
            self.updateSCHRms(midPrice)
            self._schOBS = obs
            maxP = self._schHiLo.maxPrice
            minP = self._schHiLo.minPrice
            if midPrice >= maxP and (obs.header.eventTime - self._schLastTradeTime > self._timeBetweenTrades):
                logger.info("Try to get a Buy @:%s", obs)
                '''Hitting to get a fill'''
                self.tradeSCH(obs.bestAsk, 1)
                self._schLastTradeTime = self._lastUpdateTime
            elif midPrice <= minP and (obs.header.eventTime - self._schLastTradeTime > self._timeBetweenTrades):
                logger.info("Try to get a Sell @:%s", obs)
                '''Hitting to get a fill'''
                self.tradeSCH(obs.bestBid, -1)
                self._schLastTradeTime = self._lastUpdateTime
            self._schHiLo.addEntry(midPrice, obs.header.eventTime)

        elif obs.header.instrumentId == self._scs.instrumentId:
            '''updating Rms buyMin buyMax and sellMin sellMax prices'''
            self.updateSCSRms(midPrice)
            self._scsOBS = obs
            maxP = self._scsHiLo.maxPrice
            minP = self._scsHiLo.minPrice
            if midPrice >= maxP and (obs.header.eventTime - self._scsLastTradeTime > self._timeBetweenTrades):
                logger.info("Try to get a Buy @:%s", obs)
                '''Hitting to get a fill'''
                self.tradeSCS(obs.bestAsk, 1)
                self._scsLastTradeTime = self._lastUpdateTime
            elif midPrice <= minP and (obs.header.eventTime - self._scsLastTradeTime > self._timeBetweenTrades):
                logger.info("Try to get a Sell @:%s", obs)
                '''Hitting to get a fill'''
                self.tradeSCS(obs.bestBid, -1)
                self._scsLastTradeTime = self._lastUpdateTime
            self._scsHiLo.addEntry(midPrice, obs.header.eventTime)

    def hCan(self, obs: OBStatus, canTick: TbtTickNewCan):
        pass

    def hConfNew(self, order: Order, success: bool, eventTime: datetime.datetime, reason: str):
        if success:
            if order.orderManagerId == self._schOMS.orderManagerId:
                logger.info("#%s:Order placed at @%s", self._sch.tickerName, eventTime)
            else:
                assert order.orderManagerId == self._scsOMS.orderManagerId
                logger.info("#%s:Order placed at @%s", self._scs.tickerName, eventTime)

    def hFill(self, order: Order, p: Decimal, q: int, eventTime: datetime.datetime):
        if order.orderManagerId == self._schOMS.orderManagerId:
            self._schLastTradeTime = eventTime
            self._schPnl.addTrd(p, q, eventTime,f"#Trade:SCH @( {p}, {q}, {eventTime} )")
        else:
            self._scsLastTradeTime = eventTime
            assert order.orderManagerId == self._scsOMS.orderManagerId
            self._scsPnl.addTrd(p, q, eventTime,f"#Trade:SCS @( {p}, {q}, {eventTime} )")

    def hFinished(self, order: Order):
        logger.info("This order got finished: %s", order)

    def getStrategyName(self) -> str:
        return "HiLoHit"

    def getStrategyType(self):
        return ExecutionType.Hit

    def startAllDispatcher(self):
        self._schDispatcher.connect()
        self._scsDispatcher.connect()

    def closeAllDispatcher(self):
        self._schDispatcher.close()
        self._scsDispatcher.close()

    def startStrategy(self):
        self.startAllDispatcher()
        self._tickDispatcher.beginEvents()


def __main__():
    tdb1 = Tradable(InstrumentType.Equity, 1, "SCH", Decimal('0.01'), 1, True)
    tdb2 = Tradable(InstrumentType.Equity, 2, "SCS", Decimal('0.001'), 1, True)

    rc1 = RmsCoordinator(tdb1)
    rc2 = RmsCoordinator(tdb2)
    ic = InstrumentContainer()
    ic.addInstrument(tdb1)
    ic.addInstrument(tdb2)

    tbtProcessor = TbtProcessor(ic)

    ob1 = TickPrintOrderbook(tdb1, tbtProcessor)
    ob2 = TickPrintOrderbook(tdb2, tbtProcessor)

    stratListenPort = 8000
    Strat = HitStrategy(tdb1, tdb2, tbtProcessor, ob1, ob2, rc1, rc2, schPort=8080, scsPort=9000, stratPort=stratListenPort)
    Strat.startStrategy()


if __name__ == '__main__':
    __main__()








