import datetime
from enum import Enum
import numpy as np
from decimal import Decimal

class InstrumentType(Enum):
    NotAnInstrument = 1
    Index = 2
    Currency = 3
    TreasuryBill = 4
    Swap = 5
    Bond = 6
    Equity = 7
    Future = 8
    Option = 9


class OptionType(Enum):
    CE = 1
    PE = 2



class Instrument(object):
    def __init__(self, instrumentType: InstrumentType, instrumentId: int, tickerName: str,
                 tickSize: Decimal, exchangeName=""):
        self.instrumentType = instrumentType
        self.instrumentId = instrumentId
        self.tickerName = tickerName
        self.tickSize = tickSize
        self.exchangeName = exchangeName
        assert tickSize > 0

    def toString(self):
        return self.tickerName


class Index(Instrument):
    def __init__(self, instrumentId: int, tickerName: str, tickSize: Decimal, components: list, multipliers: list):
        super().__init__(InstrumentType.Index, instrumentId, tickerName, tickSize)
        self.components = components
        self.multipliers = multipliers
        assert len(self.components) == len(self.multipliers)

    def getComponents(self):
        return self.components

    def setComponents(self, components):
        self.components = components

    def setMultipliers(self, multipliers):
        self.multipliers = multipliers

    def getMultipliers(self):
        return self.multipliers

    def computeIndexFrom(self, componentValues):
        assert len(self.components) == len(componentValues)
        total = sum(np.multiply(self.multipliers, componentValues))
        return total


class Tradable(Instrument):
    def __init__(self, instrumentType, instrumentId: int, tickerName: str, tickSize: Decimal,
                 lotSize: int, permittedToTrade: bool):
        super().__init__(instrumentType, instrumentId, tickerName, tickSize)
        self.lotSize = lotSize
        self.permittedToTrade = permittedToTrade

        self._prevClose = 0
        self._lowRange = 0
        self._highRange = 0

    def setprevClose(self, prevClose):
        self._prevClose = prevClose

    def prevClose(self):
        return self._prevClose

    def sethighRange(self, highRange):
        self._highRange = highRange

    def highRange(self):
        return self._highRange

    def setlowRange(self, lowRange):
        self._lowRange = lowRange

    def lowRange(self):
        return self._lowRange


class Equity(Tradable):
    def __init__(self, instrumentId: int, tickerName: str, tickSize: Decimal, lotSize: int, permittedToTrade: bool):
        super().__init__(InstrumentType.Equity, instrumentId, tickerName, tickSize, lotSize, permittedToTrade)


class Derivative(Tradable):
    def __init__(self, instrumentType, instrumentId: int, tickerName: str, tickSize: Decimal,
                 underlying: Instrument, expiryDate: datetime.date, lotSize: int, permittedToTrade: bool):
        super().__init__(instrumentType, instrumentId, tickerName, tickSize, lotSize, permittedToTrade)
        self.underlying = underlying
        self.expiryDate = expiryDate


class Future(Derivative):
    def __init__(self, instrumentId: int, tickerName: str, tickSize: Decimal, underlying: Instrument,
                 expiryDate: datetime.date, lotSize: int, permittedToTrade: bool, isPhysicallySettled: bool):
        super().__init__(InstrumentType.Future, instrumentId, tickerName, tickSize, underlying,
                         expiryDate, lotSize, permittedToTrade)
        self.isPhysicallySettled = isPhysicallySettled


class Option(Derivative):
    def __init__(self, instrumentId: int, tickerName: str, tickSize: Decimal, underlying: Instrument,
                 expiryDate: datetime.date, lotSize: int, optionType: OptionType, strikePrice: Decimal,
                 permittedToTrade: bool, isPhysicallySettled: bool):
        super().__init__(InstrumentType.Future, instrumentId, tickerName, tickSize, underlying,
                         expiryDate, lotSize, permittedToTrade)
        self.isPhysicallySettled = isPhysicallySettled
        self.optionType = optionType
        self.strikePrice = strikePrice


# Class to hold multiple Instruments = InstrumentContainer
class InstrumentContainer(dict):
    def addInstrument(self, newInst: Instrument):
        if not isinstance(newInst, Instrument):
            return NotImplemented
        assert newInst.instrumentId is not None
        assert newInst.tickerName is not None
        self[newInst.instrumentId] = newInst

    def fetchFromId(self, idx: int) -> Instrument:
        return self.get(idx)

    def fetchFromTicker(self, ticker: str) -> Instrument:
        for k,v in self.items():
            if v.tickerName == ticker:
                return v

    def removeInstrument(self, inst):
        if(type(inst) == Instrument):       # instrument
            for k,v in self.items():
                if v == inst:
                    self.pop(k)
        elif(type(inst) == str):            # tickerName
            for k,v in self.items():
                if v.tickerName == inst:
                    self.pop(k)
        elif(type(inst) == int):            # instrumentId
            for k,v in self.items():
                if k == inst:
                    self.pop(k)
