# This is the order management system module
import datetime
import sys
from src.bin.markets.instruments import *
from src.bin.markets.oms.rms import *
from src.bin.markets.oms.messages import *
from src.bin.infra.events.dispatcher import *
from src.bin.markets.oms.obstatus import *
from copy import copy
import src.config.logger as log
logger = log.logger


class OrderManager(object):
    orderManagerId: int
    omsTag: int
    omsTagName: str
    rmsCoordinator: RmsCoordinator
    killswitch: KillSwitch
    allOS: AllOrdersStates
    ordersCount = 1            # 0 means rms denied
    algoId: int
    tradable: Tradable
    instrumentId: int
    isIOC: bool
    # isFirstTime = True
    _dispatcher: Dispatcher

    def __init__(self, tradable: Tradable, rc: RmsCoordinator, omsId: int, omsTag: int, omsTagName: str, disp: Dispatcher, algoId=1, isIOC=True):
        self.tradable = tradable
        self.rmsCoordinator = rc
        self._dispatcher = disp
        self.orderManagerId = omsId
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

        if not self.tradable.permittedToTrade:
            self.killswitch.disallowTrading()
            logger.info("OMS created but Instrument not permitted to trade")

        self.eventNewStatus = None
        self.eventCanStatus = None
        self.eventModStatus = None
        self.eventFill = None
        self.eventFinished = None

    def getRms(self):
        return self.rmsCoordinator

    def addEventListeners(self, eventNewStatus, eventCanStatus, eventModStatus, eventFill, eventFinished):
        '''
        IMPORTANT ASSIGNMENT OF FUNCTIONS FROM STRATEGY
        Passing Functions from Strategy to be called in order manager and execute within strategy
        '''
        self.eventNewStatus = eventNewStatus
        self.eventCanStatus = eventCanStatus
        self.eventModStatus = eventModStatus
        self.eventFill = eventFill
        self.eventFinished = eventFinished

    def getOrderState(self, order) -> OrderState:
        assert order.orderManagerId == self.orderManagerId
        assert order.orderNumber > 0 and order.orderNumber < self.ordersCount
        return self.allOS[order.orderNumber].orderState

    def orderNewCheck(self, newP, newQ, eventTime: datetime.datetime) -> dict:
        allowTrade = self.rmsCoordinator.checkNew(newP, newQ)
        ordNew = OrderNew()
        if allowTrade:
            logger.info("Trade allowed by RMS:%s", self.rmsCoordinator.instrument.tickerName)
            ordNew.orderManagerId = self.orderManagerId
            ordNew.orderNumber = self.ordersCount
            self.ordersCount += 1
            ordNew.instrumentId = self.instrumentId
            ordNew.price = newP
            ordNew.qty = newQ
            ordNew.immediateOrCancel = self.isIOC
            ordNew.eventTime = eventTime
        return {'allow': allowTrade, 'ordNew': ordNew}

    def orderNewExec(self, obscopy: OBStatus, ordNew: OrderNew) -> Order:
        self.rmsCoordinator.execNew(ordNew.price, ordNew.qty)
        self.allOS.addCreateOrdState(ordNew.orderNumber)
        self.allOS.getOrdState(ordNew.orderNumber).order = Order(ordNew.orderManagerId, ordNew.orderNumber)
        self.allOS.getOrdState(ordNew.orderNumber).desiredPrice = ordNew.price
        self.allOS.getOrdState(ordNew.orderNumber).desiredQty = ordNew.qty
        self.allOS.getOrdState(ordNew.orderNumber).priceAtExchange = ordNew.price
        self.allOS.getOrdState(ordNew.orderNumber).qtyOpen = ordNew.qty
        self.allOS.getOrdState(ordNew.orderNumber).qtyFilled = 0
        '''Dispatching the OrderState and BookStatus to exchange'''
        '''Assuming that the strategy will ONLY SEND NEW ORDERS. NO MODIFY AND NO CANCELS'''
        '''Dispatching orderState so that the Exchange can tell if there is a fill'''
        dispatch = (obscopy, self.allOS.getOrdState(ordNew.orderNumber))
        logger.info("Dispatching Order to exchange:%s %s", obscopy, ordNew)
        self._dispatcher.sendDataPack(dispatch)
        return self.allOS.getOrdState(ordNew.orderNumber).order

    def orderNew(self, obs: OBStatus, newP, newQ, eventTime: datetime.datetime):
        '''Will be called from Strategy'''
        obscopy = copy(obs)
        checkVal = self.orderNewCheck(newP, newQ, eventTime)
        if checkVal['allow']:
            logger.info("Executing Order New:%s %s",OrderToAdaptMsg.OrderNew, checkVal['ordNew'])
            return self.orderNewExec(obscopy, checkVal['ordNew'])
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

    def orderCanExec(self, obscopy: OBStatus, ordCan: OrderCan) -> Order:
        assert ordCan.orderManagerId == self.orderManagerId
        assert ordCan.orderManagerId < self.ordersCount
        ordState = self.allOS.getOrdState(ordCan.orderNumber)
        assert ordState.isConfirmed
        if not ordState.isFinished:
            ordState.desiredQty = 0
        ordState.isCancelSent = True
        '''Dispatching the Order and BookStatus to exchange'''
        '''This is the correct way of sending orders, but this will not be called'''
        dispatch = (obscopy, Order(self.orderManagerId, ordCan.orderNumber))
        self._dispatcher.sendDataPack(dispatch)
        return Order(self.orderManagerId, ordCan.orderNumber)

    def orderCan(self, obs: OBStatus, whichOrder: Order, eventTime: datetime.datetime):
        '''Will be called from Strategy'''
        obscopy = copy(obs)
        checkVal = self.orderCanCheck(whichOrder, eventTime)
        if checkVal['allow']:
            logger.info("%s %s",OrderToAdaptMsg.OrderCan, checkVal['ordCan'])
            self.orderCanExec(obscopy, checkVal['ordCan'])
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

    def orderModExec(self, obscopy, ordMod: OrderMod) -> Order:
        assert ordMod.orderManagerId == self.orderManagerId
        assert ordMod.instrumentId == self.instrumentId
        assert ordMod.orderManagerId < self.ordersCount
        ordState = self.allOS.getOrdState(ordMod.orderNumber)
        assert ordState.isConfirmed and not ordState.isFinished
        ordState.desiredQty = ordMod.modifyQty
        ordState.desiredPrice = ordMod.modifyPrice
        ordState.isModifySent = True
        '''Dispatching the Order and BookStatus to exchange'''
        '''This is the correct way of sending orders, but this will not be called'''
        dispatch = (obscopy, Order(self.orderManagerId, ordMod.orderNumber))
        self._dispatcher.sendDataPack(dispatch)
        return Order(self.orderManagerId, ordMod.orderNumber)

    def orderMod(self, obs: OBStatus, whichOrder: Order, modPrice: bool, newP: Decimal, modQty: bool,
                 newQ: int, eventTime: datetime.datetime):
        '''Will be called from Strategy'''
        obscopy = copy(obs)
        checkVal = self.orderModCheck(whichOrder, modPrice, newP, modQty, newQ, eventTime)
        if checkVal['allow']:
            self.orderModExec(obscopy, checkVal['ordMod'])
            return True
        else:
            return False

    def handleConfirmNew(self, confirmNew: ConfirmNew):
        assert confirmNew.orderManagerId == self.orderManagerId, f"{confirmNew.orderManagerId} {self.orderManagerId} {self.instrumentId}"
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

    def processExchangeMsg(self):
        '''
        Will be called from Strategy
        Generally it is a constant listener, but here we will call it from strategy.
        CALL FROM STRAT, JUST AFTER SENDING AN ORDER
        '''
        confirmNew = pickle.loads(self._dispatcher._sock.recv(4096))
        assert isinstance(confirmNew, ConfirmNew)
        logger.info("OMS:%s Got ConfirmNew:%s", self.instrumentId, confirmNew)
        self.handleConfirmNew(confirmNew)

        fill = pickle.loads(self._dispatcher._sock.recv(4096))
        logger.info("OMS:%s Got Fill:%s", self.instrumentId, fill)
        if fill == "No_FILL":
            return
        else:
            assert isinstance(fill, Fill)
            self.handleFill(fill)






























