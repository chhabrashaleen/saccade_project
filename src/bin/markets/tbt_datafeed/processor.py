import src.config.logger as log
from src.bin.markets.tbt_datafeed.messages import *
logger = log.logger


class TbtProcessor:
    _ic: InstrumentContainer
    _instrumentId: int
    _feedIsUp = False
    _isLiveMode = False
    _hasStarted = False
    _hasGoneLive = False
    _hasFinished = False

    def __init__(self, idx=1, isLiveMode=False):
        self._instrumentId = idx
        self._isLiveMode = isLiveMode
        self.callNew = None
        self.callCan = None
        self.callMod = None
        self.callTrd = None

    def getInstrumentId(self):
        return self._instrumentId

    def readEvent(self, tick: TickRead):
        '''
        Will not fetch UNK Trade Ticks with "Zero" ExchangeOrderId, assuming them to be trade rejections.
        '''
        if tick.tickType == TbtTickTypes.Ignore:
            # logger.warn("###IGNORE_UNK:%s", tick)
            return
        (tickType, goTick) = self._processTick(tick)
        if tickType == TbtTickTypes.New:
            self.callNew(goTick)
        elif tickType == TbtTickTypes.Mod:
            self.callMod(goTick)
        elif tickType == TbtTickTypes.Can:
            self.callCan(goTick)
        elif tickType == TbtTickTypes.Trd:
            self.callTrd(goTick)
            '''TODO: Improvise'''

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
        assert self._instrumentId == instId
        if tickType == TbtTickTypes.New:
            self.callNew = toWhichFn
        elif tickType == TbtTickTypes.Mod:
            self.callMod = toWhichFn
        elif tickType == TbtTickTypes.Can:
            self.callCan = toWhichFn
        elif tickType == TbtTickTypes.Trd:
            self.callTrd = toWhichFn

