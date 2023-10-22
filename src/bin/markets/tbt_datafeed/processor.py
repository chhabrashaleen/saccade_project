import src.config.logger as log
from src.bin.markets.tbt_datafeed.messages import *
logger = log.logger
import time

class TbtProcessor:
    _ic: InstrumentContainer
    _feedIsUp = False
    _isLiveMode = False
    _hasStarted = False
    _hasGoneLive = False
    _hasFinished = False
    callNew = {}
    callCan = {}
    callMod = {}
    callTrd = {}
    '''Sleeping for 1ms between each tick reading'''
    _sleepTimeMs = 5

    def __init__(self, ic: InstrumentContainer, isLiveMode=False):
        self._ic = ic
        self._isLiveMode = isLiveMode

        for idx in self._ic.keys():
            self.callNew[idx] = None
            self.callCan[idx] = None
            self.callMod[idx] = None
            self.callTrd[idx] = None

    def getInstrumentContainer(self):
        return self._ic

    def readEvent(self, tick: TickRead):
        '''
        Will not fetch UNK Trade Ticks with "Zero" ExchangeOrderId, assuming them to be trade rejections.
        '''
        if tick.tickType == TbtTickTypes.Ignore:
            # logger.warn("###IGNORE_UNK:%s", tick)
            return
        (tickType, goTick) = self._processTick(tick)
        assert not isinstance(goTick, TickRead)
        if tickType == TbtTickTypes.New:
            self.callNew[goTick.header.instrumentId](goTick)
        elif tickType == TbtTickTypes.Mod:
            self.callMod[goTick.header.instrumentId](goTick)
        elif tickType == TbtTickTypes.Can:
            self.callCan[goTick.header.instrumentId](goTick)
        elif tickType == TbtTickTypes.Trd:
            self.callTrd[goTick.header.instrumentId](goTick)
        time.sleep(self._sleepTimeMs/1000)

    def _processTick(self, tick: TickRead):
        header = TbtTickHeader(tick.instrumentId, tick.eventTime)
        assert tick.tickType != TbtTickTypes.Ignore
        goTick = None
        if tick.tickType == TbtTickTypes.New:
            goTick = TbtTickNewCan(header, tick.exchangeOrderNumber, tick.price, tick.quantity)
        elif tick.tickType == TbtTickTypes.Mod:
            '''This has to change if we see that the data also has modify ticks'''
            goTick = TbtTickMod(header, tick.exchangeOrderNumber, tick.price, tick.quantity, 0, 0, 0)
        elif tick.tickType == TbtTickTypes.Can:
            goTick = TbtTickNewCan(header, tick.exchangeOrderNumber, tick.price, tick.quantity)
        elif tick.tickType == TbtTickTypes.Trd:
            if tick.quantity >= 0:
                '''this was a hit on the bid side.
                Someone has sold by hitting at bestBid hence no change on the ask side'''
                goTick = TbtTickTrd(header, tick.exchangeOrderNumber, 0, tick.price,
                                    abs(tick.quantity), tick.price, tick.price)
            elif tick.quantity < 0:
                '''this was a hit on the ask side.
                Someone has bought by hitting at bestAsk hence no change on the bid side'''
                goTick = TbtTickTrd(header, 0, tick.exchangeOrderNumber, tick.price,
                                    abs(tick.quantity), tick.price, tick.price)
        return (tick.tickType, goTick)

    def addTickHandler(self, tickType: TbtTickTypes, instId: int, toWhichFn):
        assert instId in self._ic.keys()
        if tickType == TbtTickTypes.New:
            self.callNew[instId] = toWhichFn
        elif tickType == TbtTickTypes.Mod:
            self.callMod[instId] = toWhichFn
        elif tickType == TbtTickTypes.Can:
            self.callCan[instId] = toWhichFn
        elif tickType == TbtTickTypes.Trd:
            self.callTrd[instId] = toWhichFn

