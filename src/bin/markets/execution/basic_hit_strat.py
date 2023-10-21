# This module is a basic hit execution strategy using the designed framework
import datetime

from src.bin.markets.oms.oms import *
from src.bin.markets.oms.rms import *
from src.bin.markets.oms.messages import *
from src.bin.markets.instruments import *
from src.bin.markets.pnl import *
from src.bin.markets.execution.messages import *
from src.bin.markets.oms.processor import *
import math


class HitExecStrategy(ExecutionStrategy):

    _oid: Order # orderID
    _quitExecution: bool
    _remainingFillQty: int
    _rc: RmsCoordinator
    _ob: OrderBook
    _oms: OrderManager
    _execCoordinator: ExecutionCoordinator
    _nextOrderAttemptTime: datetime.datetime
    _bpsMargin: int
    _tickSize: Decimal
    _strategyId: int

    def __init__(self, _tdb: Tradable, _bpsMargin: int, _ob: OrderBook, _rc: RmsCoordinator,
                 _execCoord: ExecutionCoordinator, _algoId: int, _omsProc: OmsProcessor,
                 _omsTag: int, _omsTagName = None):
        self._rc = _rc
        self._ob = _ob
        self._execCoord = _execCoord
        self._bpsMargin = _bpsMargin
        self._quitExecution = False
        self._oid = Order(0,0)          # Initializing Order

        self._oms = OrderManager(_tdb, _rc, _omsTag, _omsTagName, _algoId)
        self._oms.addEventListeners(self.handleNew, self.handleCan, None, self.hanleFill, None)
        self._ob.addDispatch(self.hTick, self.hTick, self.hTick, self.hTick)

    def _executeHelper(self, eventTime: datetime.datetime):
        assert self._oid == Order(0,0) or self._oms.getOrderState(self._oid).isFinished
        if self._quitExecution or self._remainingFillQty == 0:
            self._quitExecution = False
            self._oid = Order(0,0)
            self._remainingFillQty = 0
            assert not self.isExecuting()
            
        else:
            ordQty = self._remainingFillQty
            assert ordQty != 0


    def getStrategyName(self) -> str:
        return "BlindHit"

    def getStrategyId(self) -> int:
        return self._strategyId

    def setStrategyId(self, idx: int):
        self._strategyId = idx

    def getStratType(self):
        return ExecutionType.Hit

    def isExecuting(self) -> bool:
        return self._remainingFillQty != 0

    def execute(self, targetQty: int, currentQty: int, eventTime: datetime.datetime) -> bool:
        assert not self.isExecuting()
        assert isinstance(self._oid, Order)

        self._remainingFillQty = targetQty - currentQty
        assert self._remainingFillQty != 0
        self._manageExecution(eventTime)
        return True









