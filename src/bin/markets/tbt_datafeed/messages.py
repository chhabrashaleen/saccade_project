# This modules gives messages for tick printing for the orderbook
from src.bin.markets.instruments import *


class TbtTickTypes(Enum):
    New = 1
    Mod = 2
    Can = 3
    Trd = 4
    ClearOrderBook = 5
    Ignore = 6

class BookStatus(Enum):
    Unknown = 1
    Open = 2
    Closed = 3
    PreOpen = 4


class TbtTickHeader(object):
    instrumentId: int
    eventTime: datetime.datetime

    def __init__(self, instId, eventTime):
        self.instrumentId = instId
        self.eventTime = eventTime


class TbtTickNewCan(object):
    header: TbtTickHeader
    exchangeOrderNumber: int
    price: Decimal
    quantity: int

    def __init__(self, header, exchOrd, p, q):
        self.header = header
        self.exchangeOrderNumber = exchOrd
        self.price = p
        self.quantity = q

    def __str__(self):
        return ("#TICK_NEWCAN: eventTime:%s; exchangeOrderNumber:%s; price:%s; quantity:%s"
                % (self.header.eventTime, self.exchangeOrderNumber, self.price, self.quantity))


class TbtTickMod(object):
    header: TbtTickHeader
    exchangeOrderNumber: int
    newPrice: Decimal
    newQuantity: int
    oldPrice: Decimal
    oldQuantity: int
    newExchangeOrderNumber: int

    def __init__(self, header, exchOrd, np, nq, op, oq, nexchOrd):
        self.header = header
        self.exchangeOrderNumber = exchOrd
        self.newPrice = np
        self.newQuantity = nq
        self.oldPrice = op
        self.oldQuantity = oq
        self.newExchangeOrderNumber = nexchOrd

    def __str__(self):
        return ("#TICK_MODIFY: eventTime:%s; exchangeOrderNumber:%s; newPrice:%s; newQuantity:%s; oldPrice:%s; oldQuantity:%s"
                % (self.header.eventTime, self.exchangeOrderNumber, self.newPrice, self.newQuantity, self.oldPrice,
                   self.oldQuantity))


class TbtTickTrd(object):
    header: TbtTickHeader
    exchangeOrderNumberBuy: int
    exchangeOrderNumberSell: int
    tradedPrice: Decimal
    tradedQuantity: int
    buyOrderPrice: Decimal
    sellOrderPrice: Decimal

    def __init__(self, header, exchOrdBuy, exchOrdSell, tp, tq, bp, sp):
        self.header = header
        self.exchangeOrderNumberBuy = exchOrdBuy
        self.exchangeOrderNumberSell = exchOrdSell
        assert self.exchangeOrderNumberBuy <= 0 or self.exchangeOrderNumberSell <= 0
        self.tradedPrice = tp
        self.tradedQuantity = tq
        self.buyOrderPrice = bp
        self.sellOrderPrice = sp


    def __str__(self):
        return ("#TICK_TRADE: eventTime:%s; exchangeOrderNumberBuy:%s; exchangeOrderNumberSell:%s; tradedPrice:%s; tradedQuantity:%s"
                %(self.header.eventTime,
                  self.exchangeOrderNumberBuy,self.exchangeOrderNumberSell,
                  self.tradedPrice, self.tradedQuantity))


class StatusUpdate:
    header: TbtTickHeader
    status: BookStatus


class TickRead(object):
    eventTime: datetime.datetime
    exchangeOrderNumber: int
    basicTickerName: str
    instrumentId: int
    tickSize: Decimal
    tickType: TbtTickTypes
    price: Decimal
    quantity: int

    def __init__(self, eventTime, exchangeOrderNumber, basicTickerName, side, tickStr, price, quantity,
                 instrumentId, tickSize):
        if tickStr == "NEW":
            self.tickType = TbtTickTypes.New
        elif tickStr == "CANCEL":
            self.tickType = TbtTickTypes.Can
        elif tickStr == "TRADE":
            self.tickType = TbtTickTypes.Trd

        self.eventTime = eventTime
        self.exchangeOrderNumber = exchangeOrderNumber
        self.basicTickerName = basicTickerName
        self.price = price
        self.tickSize = tickSize
        self.instrumentId = instrumentId

        assert price % tickSize == 0

        if side == "BUY":
            self.quantity = abs(quantity)
        elif side == "SELL":
            self.quantity = -1 * abs(quantity)
        elif side == 'UNK':
            '''Redefining the tick type to be ignored'''
            self.tickType = TbtTickTypes.Ignore
            self.quantity = abs(quantity)

    def __str__(self):
        return ("#TICK: eventTime:%s; exchangeOrderNumber:%s; tickerName:%s; tickType:%s; price:%s; quantity:%s"
                %(self.eventTime, self.exchangeOrderNumber, self.basicTickerName, self.tickType,
                  self.price, self.quantity))
