import sys
from src.bin.markets.tbt_datafeed.tick_dispatcher import *
from src.bin.markets.tbt_datafeed.messages import *
from src.bin.markets.oms.processor import *
from src.bin.markets.oms.obstatus import *
import src.config.logger as log
from decimal import Decimal
from copy import copy
logger = log.logger


class Level:
    quantity: int
    price: Decimal

    def __init__(self, q, p):
        self.quantity = q
        self.price = p


class TickPrintOrderbook(object):
    """
    ASSUMPTION:
    In order to keep it simple.
    There is only one level on bid side and one on ask side.
    All the bid quantities are placed at bestBid and all the ask quantities are placed at bestAsk.

    If needed the orderbook can be developed fully into multiple bids and multiple asks levels.
    That will require some comprehensive effort in developing the component infrastructure.
    """
    _tickCount: int
    _bestBid = -sys.maxsize
    _bestAsk = sys.maxsize
    _lastUpdateTime = datetime.datetime.min
    _latestSaneBestBid = -sys.maxsize
    _latestSaneBestAsk = sys.maxsize
    _tickSize: Decimal

    _bookArrayMinPrice = sys.maxsize        # Assuming the circuit limit to be at 10%
    _bookArrayMaxPrice = -sys.maxsize       # Assuming the circuit limit to be at 10%
    _bookBids: list[int]
    _bookAsks: list[int]
    _bookDataCount: int

    _lastTradedPrice: Decimal
    _lastTradedTime: datetime.datetime.min
    _lastTradedQuantity: int
    _tradedTurnover = 0
    _tradedQuantity = 0

    _tickBeingProcessed = False
    _tradeBeingProcessed = False
    _dispatchOnlyBest = True
    _dispatchOnlySane = True

    def __init__(self, inst: Tradable, tbtProc: TbtProcessor, omsProc: OmsProcessor):
        self.tbtProcessor = tbtProc
        self.omsProcessor = omsProc
        self.instrument = inst
        self._tickSize = inst.tickSize
        self.newDispatchFn = None
        self.canDispatchFn = None
        self.modDispatchFn = None
        self.trdDispatchFn = None
        self._tickCount = 0
        self._isInitialized = False
        self._OBStatus = None

        self.tbtProcessor.addTickHandler(TbtTickTypes.New, inst.instrumentId, self.handleNew)
        self.tbtProcessor.addTickHandler(TbtTickTypes.Can, inst.instrumentId, self.handleCan)
        self.tbtProcessor.addTickHandler(TbtTickTypes.Mod, inst.instrumentId, self.handleMod)
        self.tbtProcessor.addTickHandler(TbtTickTypes.Trd, inst.instrumentId, self.handleTrd)

    def addDispatch(self, newFn, canFn, modFn, trdFn):
        if newFn is not None:
            self.newDispatchFn = newFn
        if canFn is not None:
            self.canDispatchFn = canFn
        if modFn is not None:
            self.modDispatchFn = modFn
        if trdFn is not None:
            self.trdDispatchFn = trdFn

    def __str__(self):
        return ("#ORDERBOOK:%s instrumentId:%s; bestBid(%s %s); bestAsk(%s %s); sane=%s "
                % (self._lastUpdateTime, self.tbtProcessor.getInstrumentId(), self.bestBid(), self.bestBidQty(),
                   self.bestAsk(), self.bestAskQty(), self.isSane()))

    def bestBid(self):
        if self._bestBid < -sys.maxsize/2:
            return 0
        return self._bestBid

    def bestAsk(self):
        if self._bestAsk > sys.maxsize/2:
            return 0
        return self._bestAsk

    def bestBidQty(self):
        if self._bestBid < -sys.maxsize/2:
            return 0
        assert self.hasBestBid()
        idx = int((self._bestBid - self._bookArrayMinPrice) / self._tickSize)
        return self._bookBids[idx]

    def bestAskQty(self):
        if self._bestAsk > sys.maxsize/2:
            return 0
        assert self.hasBestAsk()
        idx = int((self._bestAsk - self._bookArrayMinPrice) / self._tickSize)
        return self._bookAsks[idx]

    def hasBestBid(self):
        return self._bestBid > -sys.maxsize

    def hasBestAsk(self):
        return self._bestAsk < sys.maxsize

    def lastUpdateTime(self):
        return self._lastUpdateTime

    def lastTradedPrice(self):
        return self._lastTradedPrice

    def lastTradedTime(self):
        return self._lastTradedTime

    def lastTradedQuantity(self):
        return self._lastTradedQuantity

    def tradedTurnover(self):
        return self._tradedTurnover

    def tickCount(self):
        return self._tickCount

    def isSane(self):
        return self._bestBid < self._bestAsk

    def idxBBid(self):
        return int((self.bestBid() - self._bookArrayMinPrice)/self._tickSize)

    def idxBAsk(self):
        return int((self.bestAsk() - self._bookArrayMinPrice) / self._tickSize)

    def getOBStatus(self):
        if self._OBStatus is None:
            return OBStatus(TbtTickHeader(0,datetime.datetime.min),Decimal('0'),0,Decimal('0'),0)
        return self._OBStatus

    def findNextBid(self, startPrice):
        idx = int((startPrice - self._bookArrayMinPrice)/self._tickSize)
        assert idx >= 0 and idx < self._bookDataCount
        for j in range(idx-1, -1, -1):
            if self._bookBids[j] > 0:
                return Level(self._bookBids[j], j * self._tickSize + self._bookArrayMinPrice)
        return Level(0, -sys.maxsize)

    def findNextAsk(self, startPrice):
        idx = int((startPrice - self._bookArrayMinPrice)/self._tickSize)
        assert idx >= 0 and idx < self._bookDataCount
        for j in range(idx+1, self._bookDataCount):
            if self._bookAsks[j] < 0:
                return Level(self._bookAsks[j], j * self._tickSize + self._bookArrayMinPrice)
        return Level(0, sys.maxsize)

    def findPreviousBid(self, startPrice):
        idx = int((startPrice - self._bookArrayMinPrice)/self._tickSize)
        assert idx >= 0 and idx < self._bookDataCount
        idxBest = int((self._bestBid - self._bookArrayMinPrice)/self._tickSize) if self.hasBestBid() else idx
        for j in range(idx+1, idxBest+1):
            if self._bookBids[j] > 0:
                return Level(self._bookBids[j], j * self._tickSize + self._bookArrayMinPrice)
        return Level(0, -sys.maxsize)

    def findPreviousASk(self, startPrice):
        idx = int((startPrice - self._bookArrayMinPrice)/self._tickSize)
        assert idx >= 0 and idx < self._bookDataCount
        idxBest = int((self._bestAsk - self._bookArrayMinPrice)/self._tickSize) if self.hasBestAsk() else idx
        for j in range(idx-1, idxBest-1, -1):
            if self._bookAsks[j] < 0:
                return Level(self._bookAsks[j], j * self._tickSize + self._bookArrayMinPrice)
        return Level(0, sys.maxsize)

    def getBidQtyAtPrice(self, price):
        if price < self._bookArrayMinPrice or price > self._bookArrayMaxPrice:
            return 0
        idx = int((price - self._bookArrayMinPrice)/self._tickSize)
        assert idx >= 0 and idx < self._bookDataCount
        return self._bookBids[idx]

    def getAskQtyAtPrice(self, price):
        if price < self._bookArrayMinPrice or price > self._bookArrayMaxPrice:
            return 0
        idx = int((price - self._bookArrayMinPrice)/self._tickSize)
        assert idx >= 0 and idx < self._bookDataCount
        return self._bookAsks[idx]

    def getResidualQtyBid(self):
        assert not self.isSane()
        leftQty = self.bestBidQty()
        bestBid = self.bestBid()
        t = Level(self.bestAskQty(), self.bestAsk())
        while bestBid >= t.price and leftQty > 0:
            leftQty += t.quantity
            t = self.findNextAsk(t.price)
        return leftQty if leftQty > 0 else 0

    def getResidualQtyAsk(self):
        assert not self.isSane()
        leftQty = self.bestAskQty()
        bestAsk = self.bestAsk()
        t = Level(self.bestBidQty(), self.bestBid())
        while bestAsk <= t.price and leftQty < 0:
            leftQty += t.quantity
            t = self.findNextBid(t.price)
        return leftQty if leftQty < 0 else 0

    def residualQtyBid(self):
        return self.getResidualQtyBid() > 0

    def residualQtyAsk(self):
        return self.getResidualQtyAsk() < 0

    def initialize(self, price):
        self._bookArrayMinPrice = price * 7 / 10
        self._bookArrayMaxPrice = price * 13 / 10
        self._bookDataCount = int((self._bookArrayMaxPrice - self._bookArrayMinPrice) / self._tickSize)
        self._bookBids = [0] * self._bookDataCount
        self._bookAsks = [0] * self._bookDataCount
        self._lastTradedPrice = Decimal('0')
        self._isInitialized = True
        logger.info("OrderBook Initialized Price:%s", price)

    def handleNew(self, tData):
        self._tickCount += 1
        self._tickBeingProcessed = True
        assert isinstance(tData, TbtTickNewCan)
        if not self._isInitialized:
            self.initialize(tData.price)

        oldIsSane = self.isSane()
        if not oldIsSane and self.hasBestAsk() and self.hasBestBid():
            assert(tData.price == self._lastTradedPrice or
                   (tData.quantity < 0 and tData.price == self._bestBid) or
                   (tData.quantity > 0 and tData.price == self._bestAsk))

        assert tData.header.instrumentId == self.instrument.instrumentId
        self._lastUpdateTime = tData.header.eventTime

        pp = tData.price
        qq = tData.quantity
        assert int(pp % self._tickSize) == 0
        assert qq != 0
        assert pp >= self._bookArrayMinPrice and pp <= self._bookArrayMaxPrice, ("minP:",self._bookArrayMinPrice,"pp:",pp,"maxP:",self._bookArrayMaxPrice)

        idx = int((pp - self._bookArrayMinPrice)/self._tickSize)
        assert idx >= 0 and idx < self._bookDataCount

        changesBestQty = idx == self.idxBBid() or idx == self.idxBAsk()
        changesBestBidAsk = False
        if qq > 0:
            self._bookBids[idx] += qq
            if pp > self._bestBid:
                self._bestBid = pp
                changesBestBidAsk = True
        else: #qq < 0
            self._bookAsks[idx] += qq
            if pp < self._bestAsk:
                self._bestAsk = pp
                changesBestBidAsk = True

        # if the OB was insane before, this new should not make it sane
        if not oldIsSane:
            assert not self.isSane()

        if changesBestBidAsk and self.isSane():
            self._latestSaneBestBid = self._bestBid
            self._latestSaneBestAsk = self._bestAsk

        self._OBStatus = OBStatus(tData.header, self.bestBid(), self.bestBidQty(),
                                  self.bestAsk(), self.bestAskQty())
        if self._dispatchOnlyBest:
            if not changesBestBidAsk and not changesBestQty:
                return
        if self._dispatchOnlySane:
            if not self.isSane():
                return

        self.newDispatchFn(copy(self._OBStatus), tData)
        self.omsProcessor.processOrders(copy(self._OBStatus))
        self._tickBeingProcessed = False

    def handleCan(self, tData):
        self._tickCount += 1
        assert isinstance(tData, TbtTickNewCan)
        self._tickBeingProcessed = True
        assert tData.header.instrumentId == self.instrument.instrumentId
        self._lastUpdateTime = tData.header.eventTime
        pp = tData.price
        qq = tData.quantity
        assert int(pp % self._tickSize) == 0
        assert qq != 0
        assert pp >= self._bookArrayMinPrice and pp <= self._bookArrayMaxPrice
        idx = int((pp - self._bookArrayMinPrice)/self._tickSize)
        assert idx >= 0 and idx < self._bookDataCount

        if qq > 0:
            assert pp <= self._bestBid
            assert self._bookBids[idx] >= qq
            self._bookBids[idx] -= qq
        else:
            assert pp >= self._bestAsk
            assert self._bookAsks[idx] <= qq
            self._bookAsks[idx] -= qq

        changesBestQty = idx == self.idxBBid() or idx == self.idxBAsk()
        changesBestBidAsk = False
        if qq > 0 and pp == self._bestBid and self._bookBids[idx] <= 0:
            self.scanForNextBestBid(idx)
            changesBestBidAsk = True
        elif qq < 0 and pp == self._bestAsk and self._bookAsks[idx] >= 0:
            self.scanForNextBestAsk(idx)
            changesBestBidAsk = True

        isSane = self.isSane()
        if changesBestBidAsk and isSane:
            self._latestSaneBestBid = self._bestBid
            self._latestSaneBestAsk = self._bestAsk

        self._OBStatus = OBStatus(tData.header, self.bestBid(), self.bestBidQty(),
                                  self.bestAsk(), self.bestAskQty())
        if self._dispatchOnlyBest:
            if not changesBestBidAsk and not changesBestQty:
                return
        if self._dispatchOnlySane:
            if not self.isSane():
                return

        self.canDispatchFn(copy(self._OBStatus), tData)
        self.omsProcessor.processOrders(copy(self._OBStatus))
        self._tickBeingProcessed = False

    def handleMod(self, tData):
        self._tickCount += 1
        assert isinstance(tData, TbtTickMod)
        self._tickBeingProcessed = True
        assert tData.header.instrumentId == self.instrument.instrumentId
        self._lastUpdateTime = tData.header.eventTime

        ppNew = tData.newPrice
        qqNew = tData.newQuantity
        ppOld = tData.oldPrice
        qqOld = tData.oldQuantity

        assert int(ppNew % self._tickSize) == 0 and int(ppOld % self._tickSize) == 0
        assert (qqNew > 0 and qqOld > 0) or (qqNew < 0 and qqOld < 0)
        assert ppOld >= self._bookArrayMinPrice and ppOld <= self._bookArrayMaxPrice

        changesBestBidAsk = False
        changesBestQty = False
        if ppOld == ppNew:
            idx = int((ppOld - self._bookArrayMinPrice)/self._tickSize)
            changesBestQty = idx == self.idxBBid() or idx == self.idxBAsk()
            assert idx >= 0 and idx < self._bookDataCount
            if qqOld > 0:
                assert self._bookBids[idx] >= qqOld
                self._bookBids[idx] += (qqNew - qqOld)
            else:
                assert self._bookAsks[idx] <= qqOld
                self._bookAsks[idx] += (qqNew - qqOld)
        else:
            idxOld = int((ppOld - self._bookArrayMinPrice)/self._tickSize)
            idxNew = int((ppNew - self._bookArrayMinPrice)/self._tickSize)
            changesBestQty = idxOld == self.idxBBid() or idxOld == self.idxBAsk() or idxNew == self.idxBBid() or idxNew == self.idxBAsk()
            assert idxOld >= 0 and idxOld < self._bookDataCount
            assert idxNew >= 0 and idxNew < self._bookDataCount
            if qqOld > 0:
                self._bookBids[idxOld] -= qqOld
                self._bookBids[idxNew] += qqNew
                if ppNew > self._bestBid:
                    self._bestBid = ppNew
                    changesBestBidAsk = True
                elif ppOld == self._bestBid and self._bookBids[idxOld] == 0:
                    self.scanForNextBestBid(idxOld)
                    changesBestBidAsk = True
            else:
                self._bookAsks[idxOld] -= qqOld
                self._bookAsks[idxNew] += qqNew
                if ppNew < self._bestAsk:
                    self._bestAsk = ppNew
                    changesBestBidAsk = True
                elif ppOld == self._bestAsk and self._bookAsks[idxOld] == 0:
                    self.scanForNextBestAsk(idxOld)
                    changesBestBidAsk = True

        isSane = self.isSane()
        if changesBestBidAsk and isSane:
            self._latestSaneBestBid = self._bestBid
            self._latestSaneBestAsk = self._bestAsk

        self._OBStatus = OBStatus(tData.header, self.bestBid(), self.bestBidQty(),
                                  self.bestAsk(), self.bestAskQty())
        if self._dispatchOnlyBest:
            if not changesBestBidAsk and not changesBestQty:
                return
        if self._dispatchOnlySane:
            if not self.isSane():
                return

        self.modDispatchFn(copy(self._OBStatus), tData)
        self.omsProcessor.processOrders(copy(self._OBStatus))
        self._tickBeingProcessed = False

    def handleTrd(self, tData):
        self._tickCount += 1
        assert isinstance(tData, TbtTickTrd)
        self._tickBeingProcessed = True
        assert tData.header.instrumentId == self.instrument.instrumentId
        self._lastUpdateTime = tData.header.eventTime
        self._lastTradedTime = tData.header.eventTime
        self._lastTradedPrice = tData.tradedPrice
        assert tData.tradedQuantity > 0
        self._lastTradedQuantity = tData.tradedQuantity

        qq = tData.tradedQuantity
        ppT = tData.tradedPrice
        ppB = tData.buyOrderPrice
        ppS = tData.sellOrderPrice
        assert int(ppT % self._tickSize) == 0 and int(ppB % self._tickSize) == 0
        assert int(ppS % self._tickSize) == 0

        changesBestQty = False
        changesBestBidAsk = False
        self._tradedTurnover += qq * ppT
        self._tradedQuantity += qq

        if tData.exchangeOrderNumberBuy > 0:
            '''this was a hit on the buy side.
            Someone has sold by hitting at bestBid hence no change on the ask side'''
            idxB = int((ppB - self._bookArrayMinPrice)/self._tickSize)
            changesBestQty = idxB == self.idxBBid()
            assert idxB >= 0 and idxB < self._bookDataCount
            assert self._bookBids[idxB] >= qq
            self._bookBids[idxB] -= qq
            if self._bookBids[idxB] == 0 and ppB == self._bestBid:
                self.scanForNextBestBid(idxB)
                changesBestBidAsk = True
        elif tData.exchangeOrderNumberSell > 0:
            '''this was a hit on the ask side.
            Someone has bought by hitting at bestAsk hence no change on the bid side'''
            idxS = int((ppS - self._bookArrayMinPrice)/self._tickSize)
            changesBestQty = idxS == self.idxBAsk()
            assert idxS >= 0 and idxS < self._bookDataCount
            assert self._bookAsks[idxS] <= -qq
            self._bookAsks[idxS] += qq
            if self._bookAsks[idxS] == 0 and ppS == self._bestAsk:
                self.scanForNextBestAsk(idxS)
                changesBestBidAsk = True

        isSane = self.isSane()
        if changesBestBidAsk and isSane:
            self._latestSaneBestBid = self._bestBid
            self._latestSaneBestAsk = self._bestAsk

        self._OBStatus = OBStatus(tData.header, self.bestBid(), self.bestBidQty(),
                                  self.bestAsk(), self.bestAskQty())
        if self._dispatchOnlyBest:
            if not changesBestBidAsk and not changesBestQty:
                return
        if self._dispatchOnlySane:
            if not self.isSane():
                return

        self.trdDispatchFn(copy(self._OBStatus), tData)
        self.omsProcessor.processOrders(copy(self._OBStatus))
        self._tickBeingProcessed = False

    def scanForNextBestBid(self, idx):
        assert idx >= 0
        for j in range(idx, -1, -1):
            assert self._bookBids[j] >= 0
            if self._bookBids[j] > 0:
                self._bestBid = j * self._tickSize + self._bookArrayMinPrice
                assert self.hasBestBid()
                return
        self._bestBid = -sys.maxsize
        assert not self.hasBestBid()


    def scanForNextBestAsk(self, idx):
        assert idx >= 0
        for j in range(idx, self._bookDataCount):
            assert self._bookAsks[j] <= 0
            if self._bookAsks[j] < 0:
                self._bestAsk = j * self._tickSize + self._bookArrayMinPrice
                assert self.hasBestAsk()
                return
        self._bestAsk = sys.maxsize
        assert not self.hasBestAsk()
