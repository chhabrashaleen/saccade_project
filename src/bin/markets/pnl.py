from src.bin.markets.instruments import *
import datetime
from decimal import Decimal
import src.config.logger as log
logger = log.logger


class Pnl:
    def __init__(self, name: str, buyTcosts: Decimal, sellTcosts: Decimal, showTrades=True):
        self.__name = name+"_PNLENGINE"
        self.__buyTcosts = buyTcosts
        self.__sellTcosts = sellTcosts
        self.__showTrades = showTrades
        self.__transactionCosts = 0
        self.__tradeValue = 0
        self.__buyTcosts = 0
        self.__sellTcosts = 0
        self.__turnover = 0
        self.__openPnl = 0
        self.__closedPnl = 0
        self.__dayMTM = 0
        self.__netQty = 0
        self.__totalTradedQty = 0

    def addTrd(self, price: Decimal, qty: int, trdTime: datetime.datetime, extraInfo=""):
        assert price != 0
        self.__tradeValue += price * qty
        tcost = self.__buyTcosts if(qty >= 0) else self.__sellTcosts
        self.__transactionCosts += price * abs(qty) * tcost
        self.__turnover += price * abs(qty)

        tempNetQty = self.__netQty
        self.__netQty += qty
        self.__totalTradedQty += abs(qty)

        if (tempNetQty < 0) and (self.__netQty >= 0):
            self.__closedPnl = self.calculateDayMTM(price)
        elif (tempNetQty >= 0) and (self.__netQty < 0):
            self.__closedPnl = self.calculateDayMTM(price)

        if self.__showTrades:
            logger.info("#PNL_TRADE: %s %s %s %s %s", trdTime, self.__name, price, qty, extraInfo)
            logger.info("%s: OpenPnl:%s, ClosedPnl:%s", self.__name, self.getOpenPnl(price), self.getClosedPnl())

    def calculateDayMTM(self, lastKnownPrice: Decimal) -> Decimal:
        assert lastKnownPrice != 0
        currExposure = lastKnownPrice * self.__netQty
        dayMTM = currExposure - self.__tradeValue - self.__transactionCosts
        return dayMTM

    def getOpenPnl(self, lastKnownPrice: Decimal) -> Decimal:
        self.__openPnl = self.calculateDayMTM(lastKnownPrice) - self.__closedPnl
        return self.__openPnl

    def getClosedPnl(self):
        return self.__closedPnl

    # pnl right now in bips w.r.t turnover
    def profitsPerTrade(self, lastKnownPrice: Decimal) -> Decimal:
        assert lastKnownPrice != 0
        ppt = 0
        if self.__turnover != 0:
            dayMTM = self.calculateDayMTM(lastKnownPrice)
            ppt = 2 * 10000 * dayMTM/self.__turnover
        return ppt

    # openPNL divided by netPosition
    def getOpenPPT(self, lastKnownPrice: Decimal) -> Decimal:
        assert lastKnownPrice != 0
        openPNL = self.getOpenPnl(lastKnownPrice)
        openPPT = 0
        if self.__netQty != 0:
            _cFE = self.__netQty * lastKnownPrice
            openPPT = 10000 * openPNL / abs(_cFE)
        return openPPT
