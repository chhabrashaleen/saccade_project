# This module has definitions for Order and Status

from src.bin.markets.tbt_datafeed.messages import *
from decimal import Decimal

class Order:
    def __init__(self, orderManagerId: int, orderNumber: int):
        self.orderManagerId = orderManagerId
        self.orderNumber = orderNumber

    def blockedByRms(self):
        if self.orderNumber > 0:
            return False
        else:
            return True

    def __str__(self):
        return ("#Order(%s, %s)"%(self.orderManagerId, self.orderNumber))


class OrderState:
    order: Order
    desiredPrice: Decimal
    desiredQty: int
    priceAtExchange: Decimal
    qtyOpen: int
    qtyFilled: int
    isConfirmed = False
    isCancelSent = False
    isModifySent = False
    isFinished = False
    fillCount = 0

class AllOrdersStates(dict):
    def addCreateOrdState(self, ordNum):
        self[ordNum] = OrderState()

    def getOrdState(self, ordNum: int) -> OrderState:
        return self.get(ordNum)

class OrderBookStatusObject(object):
    header: TbtTickHeader
    bestBid: Decimal
    bestAsk: Decimal
    bestBidQuantity: int
    bestAskQuantity: int

    def __init__(self, header:TbtTickHeader, bb, bbQ, ba, baQ):
        self.header = header
        self.bestBid = bb
        self.bestBidQuantity = bbQ
        self.bestAsk = ba
        self.bestAskQuantity = baQ

    def __str__(self):
        return ("#OrderBookStatus: eventTime:%s; instrumentId:%s; bestBid:%s; bestBidQuantity:%s; bestAsk:%s; bestAskQuantity:%s"
                %(self.header.eventTime, self.header.instrumentId, self.bestBid, self.bestBidQuantity,
                  self.bestAsk, self.bestAskQuantity))

""" Aliasing the class name for easy use """
OBStatus = OrderBookStatusObject