# This module tells us about different types of Order Messages which we can receive

import datetime
from enum import Enum
from decimal import Decimal


class OrderToAdaptMsg(Enum):
    OrderNew = 1
    OrderMod = 2
    OrderCan = 3


class OrderToStrategyMsg(Enum):
    ConfirmSent = 1
    ConfirmNew = 2
    ConfirmCan = 3
    ConfirmMod = 4
    Fill = 5
    RejectNew = 6


class OrderNew(object):
    orderManagerId: int
    orderNumber: int
    instrumentId: int
    price: Decimal
    qty: int
    immediateOrCancel: bool
    eventTime: datetime.datetime

    def __str__(self):
        return ("#OrderNew: orderManagerId:%s; orderNumber:%s; price:%s; quantity:%s"
                % (self.orderManagerId, self.orderNumber, self.price, self.qty))


class OrderMod(object):
    orderManagerId: int
    orderNumber: int
    instrumentId: int
    currentPrice: Decimal
    currentOpenQty: int
    currentFilledQty: int
    modifyPrice: Decimal
    modifyQty: int
    eventTime: datetime.datetime


class OrderCan(object):
    orderManagerId: int
    orderNumber: int
    instrumentId: int
    price: Decimal
    qty: int
    eventTime: datetime.datetime


class ConfirmNew(object):
    orderManagerId: int
    orderNumber: int
    eventTime: datetime.datetime

    def __str__(self):
        return ("#ConfirmNew: orderManagerId:%s; orderNumber:%s; eventTime:%s"
                % (self.orderManagerId, self.orderNumber, self.eventTime))


class ConfirmCan(object):
    orderManagerId: int
    orderNumber: int
    eventTime: datetime.datetime
    canReason: str


class ConfirmMod(object):
    orderManagerId: int
    orderNumber: int
    newPrice: Decimal
    newQty: int
    eventTime: datetime.datetime

class Fill(object):
    orderManagerId: int
    orderNumber: int
    instrumentId: int
    price: Decimal
    qty: int
    eventTime: datetime.datetime

    def __str__(self):
        return ("#Fill: orderManagerId:%s; orderNumber:%s; price:%s; quantity:%s"
                % (self.orderManagerId, self.orderNumber, self.price, self.qty))


class RejectNew(object):
    orderManagerId: int
    orderNumber: int
    eventTime: datetime.datetime
    rejectReason: str
