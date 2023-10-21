# This module is about messages for Execution

import datetime
from enum import Enum


class Quote:
    qty: int
    price: Decimal

    def toString(self) -> str:
        return str(self.qty) + "@" + str(self.price)


class SignalType(Enum):
    Normal = 1
    ProfitBook = 2
    StopLoss = 3
    SqOff = 4


class ExecutionType(Enum):
    Hit = 1
    Quote = 2


class SignalUpdate(object):
    instId: int
    signalId: int
    type: SignalType
    execType: ExecutionType
    desiredQty: int
    referencePrice: Decimal
    signalTime: datetime.datetime


class ExecutionStrategy:
    def getStrategyName(self) -> str:
        pass

    def getStrategyId(self) -> int:
        pass

    def setStrategyId(self, idx: int):
        pass

    def getStratType(self) -> str:
        """
        This returns the Execution Type of this strategy.
        Type is one of "Hit" or "Quote"
        """
        pass

    def execute(self, targetQty: int, currentQty: int, executeTime: datetime.datetime) -> bool:
        """
        Starting point of execution assignment
        Ordered to execute (targetQty - currentQty)
        Strategy should notify execution completion
        """
        pass

    def updateExecution(self, newTargetQty: int, currentQty: int, updateTime: datetime.datetime) -> bool:
        """
        Notifies the strategy if there's a change in target quantity
        Currently only an increase in quantity to be fetched is supposed to happen using this because its hitting strat
        """
        pass

    def concludeExecution(self, fetchRemainingQty: bool):
        """
        Notifies the strategy to conclude execution ASAP.
        Expectation is that when fetchRemainingQty is true, the strategy
        would try to execute the remaining unfilled quantity
        When it's false, the strategy is expected to cancel rest of the execution
        and notify execution completion.

        This should be callable multiple times (i.e. the strategy can be called
        with isTargetPositionIncreasing = true and later with the same being false)
        """
        pass

    def getLiveQuote(self) -> Quote:
        """Returns the quote live at exchange, if any"""
        pass


class ExecutionCoordinator:
    # def allowTrading(self) -> bool:
    #     pass
    def enable(self):
        pass

    def disable(self):
        pass

    def registerStrategy(self, strat: ExecutionStrategy, probability: int):
        pass

    def isStrategyExecuting(self, strat:  ExecutionStrategy) -> bool:
        pass

    def currentTargetQty(self) -> int:
        pass

    def currentExecutionBeginQty(self) -> int:
        pass

    def onExecutionCompletion(self, strat: ExecutionStrategy, eventTime: datetime.datetime):
        pass
