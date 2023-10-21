# This module is for risk management system functions
import sys
from src.bin.markets.instruments import *
from enum import Enum


class RmsBlockedReason(Enum):
    NotBlocked = 0
    BlockedBySingleOrder = 1
    BlockedByAtMkt = 2
    BlockedByNetFilled = 3
    BlockedByTotalFilled = 4


class RmsCoordinator(object):
    _atMktBuyQty: int
    _atMktSellQty: int
    _filledNetQty: int
    _filledTotalQty: int

    # Initializing with Open limits, we can also initialize with Closed limits by defining a bool with the constructor
    _maxSingleOrderBuyQty: int(sys.maxsize)
    _maxSingleOrderSellQty: int(-sys.maxsize)
    _maxAtMktBuyQty: int(sys.maxsize)
    _maxAtMktSellQty: int(-sys.maxsize)
    _maxNetFilledQty: int(sys.maxsize)
    _maxTotalFilledQty: int(sys.maxsize)

    def __init__(self, inst: Tradable):
        self.instrument = inst
        assert self._atMktBuyQty >= 0
        assert self._atMktSellQty <= 0
        assert self._filledTotalQty >= 0

        assert self._maxSingleOrderBuyQty >= 0
        assert self._maxSingleOrderSellQty <= 0
        assert self._maxAtMktBuyQty >= 0
        assert self._maxAtMktSellQty <= 0
        assert self._maxNetFilledQty >= 0
        assert self._maxTotalFilledQty >= 0

        self._buyMinPrice = -sys.maxsize
        self._buyMaxPrice = -sys.maxsize
        self._sellMinPrice = sys.maxsize
        self._sellMaxPrice = sys.maxsize

    #   OMS Functionality

    def checkNew(self, px, q) -> bool:
        assert q != 0
        assert px % self.instrument.tickSize == 0
        assert q % self.instrument.lotSize == 0

        if q > 0:
            if ((q <= self._maxSingleOrderBuyQty) and (self._atMktBuyQty + q <= self._maxAtMktBuyQty) and
                    (self._filledNetQty + q <= self._maxNetFilledQty) and
                    (self._filledTotalQty + q <= self._maxTotalFilledQty)
                    and (px >= self._buyMinPrice) and (px <= self._buyMaxPrice)):
                return True
            else:
                return False
        else:
            if ((q >= self._maxSingleOrderSellQty) and (self._atMktSellQty + q >= self._maxAtMktSellQty) and
                    (self._filledNetQty + q >= -self._maxNetFilledQty) and
                    (self._filledTotalQty - q <= self._maxTotalFilledQty)
                    and (px >= self._sellMinPrice) and (px <= self._sellMaxPrice)):
                return True
            else:
                return False

    def execNew(self, px, q):
        assert q != 0
        assert px % self.instrument.tickSize == 0
        assert q % self.instrument.lotSize == 0
        if q > 0:
            self._atMktBuyQty += q
        else:
            self._atMktSellQty += q

    def execCan(self, px, q):
        assert q != 0
        assert px % self.instrument.tickSize == 0
        assert q % self.instrument.lotSize == 0
        if q > 0:
            assert self._atMktBuyQty >= q
            self._atMktBuyQty -= q
        else:
            assert self._atMktSellQty <= q
            self._atMktSellQty -= q

    def checkMod(self, oldpx, newpx, oldq, newq) -> bool:
        assert newq != 0
        assert oldq != 0
        assert (newq > 0 and oldq > 0) or (newq < 0 or oldq < 0)
        assert newpx % self.instrument.tickSize == 0
        assert oldpx % self.instrument.tickSize == 0
        assert newq % self.instrument.lotSize == 0
        assert oldq % self.instrument.lotSize == 0

        if oldq > 0:
            if newq > oldq:
                return self.checkNew(newpx, newq-oldq)
            else:
                if newpx >= self._buyMinPrice and newpx <= self._buyMaxPrice:
                    return True
                else:
                    return False
        elif oldq < 0:
            if newq < oldq:
                return self.checkNew(newpx, newq - oldq)
            else:
                if newpx >= self._sellMinPrice and newpx <= self._sellMaxPrice:
                    return True
                else:
                    return False

    def execMod(self, oldpx, newpx, oldq, newq):
        assert newq != 0
        assert oldq != 0
        assert (newq > 0 and oldq > 0) or (newq < 0 or oldq < 0)
        assert newpx % self.instrument.tickSize == 0
        assert oldpx % self.instrument.tickSize == 0
        assert newq % self.instrument.lotSize == 0
        assert oldq % self.instrument.lotSize == 0

        # Mod is considered as CAN + NEW for rms
        self.execCan(oldpx, oldq)
        self.execNew(newpx, newq)

    def execTrd(self, fillpx, fillq):
        assert fillq != 0
        assert fillpx % self.instrument.tickSize == 0
        assert fillq % self.instrument.lotSize == 0
        if fillq > 0:
            assert self._atMktBuyQty >= fillq
            self._atMktBuyQty -= fillq
        else:
            assert self._atMktSellQty <= fillq
            self._atMktSellQty -= fillq

        self._filledNetQty += fillq
        self._filledTotalQty += abs(fillq)

    def getAllowedMaxBuyQty(self, currentAtMktQty=0):
        assert self._maxSingleOrderBuyQty >= 0
        assert self._maxAtMktBuyQty >= 0
        assert self._atMktBuyQty >= 0
        assert self._maxNetFilledQty >= 0
        assert self._maxTotalFilledQty >= 0
        assert self._filledTotalQty >= 0

        if currentAtMktQty < 0:
            currentAtMktQty = 0

        mq = min(self._maxSingleOrderBuyQty,
                 self._maxAtMktBuyQty - self._atMktBuyQty + currentAtMktQty,
                 self._maxNetFilledQty - self._filledNetQty,
                 self._maxTotalFilledQty - self._filledTotalQty)

        return 0 if mq < 0 else mq

    def getBlockedReasonBuy(self, currentAtMktQty=0):
        if self._maxSingleOrderBuyQty <= 0:
            return RmsBlockedReason.BlockedBySingleOrder
        elif self._maxAtMktBuyQty - self._atMktBuyQty + currentAtMktQty <= 0:
            return RmsBlockedReason.BlockedByAtMkt
        elif self._maxNetFilledQty - self._filledNetQty <= 0:
            return RmsBlockedReason.BlockedByNetFilled
        elif self._maxTotalFilledQty - self._filledTotalQty <= 0:
            return RmsBlockedReason.BlockedByTotalFilled
        else:
            return RmsBlockedReason.NotBlocked

    def getAllowedMaxSellQty(self, currentAtMktQty=0):
        assert self._maxSingleOrderSellQty <= 0
        assert self._maxAtMktSellQty <= 0
        assert self._atMktSellQty <= 0
        assert self._maxNetFilledQty >= 0
        assert self._maxTotalFilledQty >= 0
        assert self._filledTotalQty >= 0

        if currentAtMktQty > 0:
            currentAtMktQty = 0

        mq = max(self._maxSingleOrderSellQty,
                 self._maxAtMktSellQty - self._atMktSellQty + currentAtMktQty,
                 -self._maxNetFilledQty - self._filledNetQty,
                 -self._maxTotalFilledQty + self._filledTotalQty)

        return 0 if mq >= 0 else mq

    def getBlockedReasonSell(self, currentAtMktQty=0):
        if self._maxSingleOrderSellQty >= 0:
            return RmsBlockedReason.BlockedBySingleOrder
        elif self._maxAtMktSellQty - self._atMktSellQty + currentAtMktQty >= 0:
            return RmsBlockedReason.BlockedByAtMkt
        elif -self._maxNetFilledQty - self._filledNetQty >= 0:
            return RmsBlockedReason.BlockedByNetFilled
        elif -self._maxTotalFilledQty + self._filledTotalQty >= 0:
            return RmsBlockedReason.BlockedByTotalFilled
        else:
            return RmsBlockedReason.NotBlocked

    def updateMaxSingleOrderBuyQty(self, qty):
        assert qty >= 0
        self._maxSingleOrderBuyQty = qty

    def updateMaxSingleOrderSellQty(self, qty):
        assert qty <= 0
        self._maxSingleOrderSellQty = qty

    def updateMaxAtMktBuyQty(self, qty):
        assert qty >= 0
        self._maxAtMktBuyQty = qty

    def updateMaxAtMktSellQty(self, qty):
        assert qty <= 0
        self._maxAtMktSellQty = qty

    def updateMaxNetFilledQty(self, qty):
        assert qty >= 0
        self._maxNetFilledQty = qty

    def updateMaxTotalFilledQty(self, qty):
        assert qty >= 0
        self._maxTotalFilledQty = qty

    def updateBuyMinMaxPrice(self, minPrice, maxPrice):
        self._buyMinPrice = minPrice
        self._buyMaxPrice = maxPrice

    def updateSellMinMaxPrice(self, minPrice, maxPrice):
        self._sellMinPrice = minPrice
        self._sellMaxPrice = maxPrice

    def getCurrAtMktBuyQty(self): return self._atMktBuyQty
    def getCurrAtMktSellQty(self): return self._atMktSellQty
    def getFilledNetQty(self): return self._filledNetQty
    def getFilledTotalQty(self): return self._filledTotalQty


class KillSwitch(object):
    def __init__(self, rc: RmsCoordinator, allowTrading=True):
        self.rc = rc
        self._allowTrading = allowTrading

    def disallowTrading(self):
        self._allowTrading = False
        self.reprocessLimits()

    def allowTrading(self):
        self._allowTrading = True
        self.reprocessLimits()

    def isTradingAllowed(self):
        return self._allowTrading

    def reprocessLimits(self):
        if self._allowTrading:
            self.rc.updateMaxSingleOrderBuyQty(sys.maxsize)
            self.rc.updateMaxSingleOrderSellQty(-sys.maxsize)
            self.rc.updateBuyMinMaxPrice(-sys.maxsize, sys.maxsize)
            self.rc.updateSellMinMaxPrice(-sys.maxsize, sys.maxsize)
        else:
            self.rc.updateMaxSingleOrderBuyQty(0)
            self.rc.updateMaxSingleOrderSellQty(0)
            self.rc.updateBuyMinMaxPrice(-sys.maxsize, -sys.maxsize)
            self.rc.updateSellMinMaxPrice(sys.maxsize, sys.maxsize)
