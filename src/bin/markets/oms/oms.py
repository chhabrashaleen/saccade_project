# This is the order management system module
import datetime
import sys
from src.bin.markets.instruments import *
from rms import *
from messages import *
from processor import *


class OrderManager(object):

    orderManagerId: int
    omsTag: int
    omsTagName: str
    rmsCoordinator: RmsCoordinator
    omsProcessor: OmsProcessor
    killswitch: KillSwitch
    allOS: AllOrdersStates
    ordersCount = 1            # 0 means rms denied
    algoId: int
    tradable: Tradable
    instrumentId: int
    isIOC: bool
    isFirstTime: True

    def __init__(self, tradable: Tradable, rc: RmsCoordinator, omsProc: OmsProcessor, omsTag: int, omsTagName: str, algoId=1, isIOC=True):
        self.tradable = tradable
        self.rmsCoordinator = rc
        self.omsProcessor = omsProc
        self.omsTag = omsTag
        self.omsTagName = omsTagName
        self.algoId = algoId
        self.isIOC = isIOC
        self.allOS = AllOrdersStates()
        assert self.tradable is not None
        assert self.rmsCoordinator is not None
        self.instrumentId = self.tradable.instrumentId
        self.orderState = OrderState()
        self.killswitch = KillSwitch(self.rmsCoordinator)

        '''OMS Processor Setup'''
        self.omsProcessor.myHandlers[OrderToStrategyMsg.ConfirmNew] = self.handleConfirmNew
        self.omsProcessor.myHandlers[OrderToStrategyMsg.ConfirmCan] = self.handleConfirmCan
        self.omsProcessor.myHandlers[OrderToStrategyMsg.ConfirmMod] = self.handleConfirmMod
        self.omsProcessor.myHandlers[OrderToStrategyMsg.Fill] = self.handleFill

        self.omsProcessor.omsTagHash.instrumentId = self.instrumentId
        self.omsProcessor.omsTagHash.omgTag = self.omsTag
        self.omsProcessor.omsTagHash.algoId = self.algoId

        self.omsProcessor.registerOms(self.omsProcessorReset, self.omsProcessor.myHandlers, self.omsProcessor.omsTagHash)

        if not self.tradable.permittedToTrade:
            self.killswitch.disallowTrading()
            print("OMS created but Instrument not permitted to trade")

        self.eventNewStatus = None
        self.eventCanStatus = None
        self.eventModStatus = None
        self.eventFill = None
        self.eventFinished = None

    # IMPORTANT ASSIGNMENT OF FUNCTIONS FROM STRATEGY
    # Passing Functions from Strategy to be called in order manager and execute within strategy
    def addEventListeners(self, eventNewStatus, eventCanStatus, eventModStatus, eventFill, eventFinished):
        self.eventNewStatus = eventNewStatus()
        self.eventCanStatus = eventCanStatus()
        self.eventModStatus = eventModStatus()
        self.eventFill = eventFill()
        self.eventFinished = eventFinished()

    def getOrderState(self, order) -> OrderState:
        assert order.orderManagerId == self.orderManagerId
        assert order.orderNumber > 0 and order.orderNumber < self.ordersCount
        return self.allOS[order.orderNumber].orderState

    def orderNewCheck(self, newP, newQ, eventTime: datetime.datetime) -> dict:
        allowTrade = self.rmsCoordinator.checkNew(newP, newQ)
        ordNew = OrderNew()
        if allowTrade:
            ordNew.orderManagerId = self.orderManagerId
            ordNew.orderNumber = self.ordersCount
            self.ordersCount += 1
            ordNew.instrumentId = self.instrumentId
            ordNew.price = newP
            ordNew.qty = newQ
            ordNew.immediateOrCancel = self.isIOC
            ordNew.eventTime = eventTime
        return {'allow': allowTrade, 'ordNew': ordNew}

    def orderNewExec(self, ordNew: OrderNew) -> Order:
        self.rmsCoordinator.execNew(ordNew.price, ordNew.qty)
        self.allOS.addCreateOrdState(ordNew.orderNumber)
        self.allOS.getOrdState(ordNew.orderNumber).desiredPrice = ordNew.price
        self.allOS.getOrdState(ordNew.orderNumber).desiredQty = ordNew.qty
        self.allOS.getOrdState(ordNew.orderNumber).priceAtExchange = ordNew.price
        self.allOS.getOrdState(ordNew.orderNumber).qtyOpen = ordNew.qty
        return self.allOS.getOrdState(ordNew.orderNumber).order

    def orderNew(self, newP, newQ, eventTime: datetime.datetime):
        checkVal = self.orderNewCheck(newP, newQ, eventTime)
        if checkVal['allow']:
            print(OrderToAdaptMsg.OrderNew," ",checkVal['ordNew'])
            return self.orderNewExec(checkVal['ordNew'])
        else:
            return Order(self.orderManagerId, 0)

    def orderCanCheck(self, order: Order, eventTime: datetime.datetime) -> dict:
        assert order.orderManagerId == self.orderManagerId
        assert order.orderManagerId < self.ordersCount
        ordState = self.allOS.getOrdState(order.orderNumber)
        assert ordState is not None
        ordCan = OrderCan()
        if (ordState.isConfirmed and (not ordState.isFinished) and (not ordState.isCancelSent)
                and self.killswitch.isTradingAllowed()):
            ordCan.orderManagerId = order.orderManagerId
            ordCan.orderNumber = order.orderNumber
            ordCan.instrumentId = self.instrumentId
            ordCan.price = ordState.priceAtExchange
            ordCan.qty = ordState.qtyOpen
            ordCan.eventTime = eventTime
            return {'allow': True, 'ordCan': ordCan}
        else:
            return {'allow': False, 'ordCan': ordCan}

    def orderCanExec(self, ordCan: OrderCan) -> Order:
        assert ordCan.orderManagerId == self.orderManagerId
        assert ordCan.orderManagerId < self.ordersCount
        ordState = self.allOS.getOrdState(ordCan.orderNumber)
        assert ordState.isConfirmed
        if not ordState.isFinished:
            ordState.desiredQty = 0
        ordState.isCancelSent = True
        return Order(self.orderManagerId, ordCan.orderNumber)

    def orderCan(self, whichOrder: Order, eventTime: datetime.datetime):
        checkVal = self.orderCanCheck(whichOrder, eventTime)
        if checkVal['allow']:
            print(OrderToAdaptMsg.OrderCan," ",checkVal['ordCan'])
        self.orderCanExec(checkVal['ordCan'])
        return checkVal['allow']

    def orderModCheck(self, whichOrder: Order, modPrice: bool, newP: Decimal, modQty: bool,
                      newQ: int, eventTime: datetime.datetime) -> dict:
        assert modPrice or modQty
        assert whichOrder.orderManagerId == self.orderManagerId
        assert whichOrder.orderNumber < self.ordersCount
        ordState = self.allOS.getOrdState(whichOrder.orderNumber)
        assert newQ != 0 or not modQty
        assert newQ == 0 or (newQ/abs(newQ) == ordState.qtyOpen/abs(ordState.qtyOpen))

        allowMod = False if (modQty and newQ) else True
        assert (ordState.isConfirmed and not ordState.isCancelSent and not ordState.isModifySent
                and not ordState.isFinished and ordState.qtyOpen != 0)

        if modQty and ordState.qtyOpen == newQ:
            modQty = False
        if modPrice and ordState.priceAtExchange == newP:
            modPrice = False
        if not modPrice and not modQty:
            allowMod = False
        if not modQty:
            newQ = ordState.qtyOpen
        if not modPrice:
            newP = ordState.priceAtExchange
        if allowMod:
            if not self.rmsCoordinator.checkMod(ordState.priceAtExchange, newP, ordState.qtyOpen, newQ):
                allowMod = False

        ordMod = OrderMod()
        if allowMod and not ordState.isFinished and ordState.isConfirmed and not ordState.isModifySent:
            ordMod.orderManagerId = whichOrder.orderManagerId
            ordMod.orderNumber = whichOrder.orderNumber
            ordMod.instrumentId = self.instrumentId
            ordMod.currentPrice = ordState.priceAtExchange
            ordMod.currentOpenQty = ordState.qtyOpen
            ordMod.modifyPrice = newP
            ordMod.modifyQty = newQ
            ordMod.eventTime = eventTime
        else:
            allowMod = False

        return {'allow': allowMod, 'ordMod': ordMod}

    def orderModExec(self, ordMod: OrderMod) -> Order:
        assert ordMod.orderManagerId == self.orderManagerId
        assert ordMod.instrumentId == self.instrumentId
        assert ordMod.orderManagerId < self.ordersCount
        ordState = self.allOS.getOrdState(ordMod.orderNumber)
        assert ordState.isConfirmed and not ordState.isFinished
        ordState.desiredQty = ordMod.modifyQty
        ordState.desiredPrice = ordMod.modifyPrice
        ordState.isModifySent = True
        return Order(self.orderManagerId, ordMod.orderNumber)

    def orderMod(self, whichOrder: Order, modPrice: bool, newP: Decimal, modQty: bool,
                 newQ: int, eventTime: datetime.datetime):
        checkVal = self.orderModCheck(whichOrder, modPrice, newP, modQty, newQ, eventTime)
        if checkVal['allow']:
            self.orderModExec(checkVal['ordMod'])
            return True
        else:
            return False

    def omsProcessorReset(self):
        # currentOutgoingMsg = self.omsProcessor.getOutgoingMsg()
        self.killswitch.disallowTrading()
        for i in range(1,self.ordersCount):
            if i in self.allOS.keys():
                os = self.allOS.getOrdState(i)
                if not os.isFinished:
                    if os.isConfirmed or os.desiredQty != 0:
                        '''Send a cancel to Strategy'''
                        self.rmsCoordinator.execCan(os.priceAtExchange, os.qtyOpen)
                        os.qtyOpen = 0
                        os.isFinished = True
                        self.eventCanStatus((Order(self.orderManagerId, i), True, datetime.datetime.min, "OMS Reset"))

    def handleConfirmNew(self, confirmNew: ConfirmNew):
        assert confirmNew.orderManagerId == self.orderManagerId
        ordState = self.allOS.getOrdState(confirmNew.orderNumber)
        assert ordState is not None
        assert (ordState.desiredQty != 0 and not ordState.isConfirmed and not ordState.isFinished
                and ordState.fillCount == 0)
        ordState.isConfirmed = True
        self.eventNewStatus(Order(confirmNew.orderManagerId, confirmNew.orderNumber), True,
                            confirmNew.eventTime, "NoReason")

    def handleConfirmCan(self, confirmCan: ConfirmCan):
        assert confirmCan.orderManagerId == self.orderManagerId
        ordState = self.allOS.getOrdState(confirmCan.orderNumber)
        assert ordState is not None
        assert ordState.isConfirmed and (not ordState.isCancelSent or not ordState.isFinished)

        self.rmsCoordinator.execCan(ordState.priceAtExchange, ordState.qtyOpen)
        ordState.isFinished = True
        ordState.qtyOpen = 0
        self.eventCanStatus(Order(confirmCan.orderManagerId, confirmCan.orderNumber), True,
                            confirmCan.eventTime, confirmCan.canReason)

    def handleConfirmMod(self, confirmMod: ConfirmMod):
        assert confirmMod.orderManagerId == self.orderManagerId
        ordState = self.allOS.getOrdState(confirmMod.orderNumber)
        self.rmsCoordinator.execMod(ordState.priceAtExchange, confirmMod.newPrice, ordState.qtyOpen, confirmMod.newQty)
        ordState.priceAtExchange = confirmMod.newPrice
        ordState.qtyOpen = confirmMod.newQty
        ordState.isModifySent = False       # isModifySent was true before, turning it false means now this order can be modified again
        self.eventModStatus(Order(confirmMod.orderManagerId, confirmMod.orderNumber), True, confirmMod.newPrice,
                            confirmMod.newQty, confirmMod.eventTime)

    # handleFill handles Fill event and Finished event both
    def handleFill(self, fill: Fill):
        assert fill.orderManagerId == self.orderManagerId
        assert fill.instrumentId == self.instrumentId
        ordState = self.allOS.getOrdState(fill.orderNumber)
        assert ordState.isConfirmed and not ordState.isFinished
        assert fill.qty != 0

        self.rmsCoordinator.execTrd(fill.price, fill.qty)
        ordState.qtyOpen -= fill.qty
        ordState.qtyFilled += fill.qty
        reduceBy = fill.qty

        if ordState.desiredQty > reduceBy:
            ordState.desiredQty -= reduceBy
        else:
            ordState.desiredQty = 0

        ordState.fillCount += 1
        if ordState.qtyOpen == 0:
            assert not ordState.isFinished
            ordState.isFinished = True

        self.eventFill(Order(fill.orderManagerId, fill.orderNumber), fill.price, fill.qty, fill.eventTime)
        if ordState.isFinished:
            self.eventFinished(Order(fill.orderManagerId, fill.orderNumber))
































