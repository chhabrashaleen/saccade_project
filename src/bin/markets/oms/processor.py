import pickle

from src.bin.markets.instruments import *
from src.bin.markets.tbt_datafeed.tick_print_orderbook import *
from src.bin.markets.oms.obstatus import *
from src.bin.markets.oms.messages import *
from src.bin.infra.events.dispatcher import *
import src.config.logger as log
logger = log.logger


class OmsTagHash:
    instrumentId: int
    omgTag: int
    omsTagName: str

class OmsProcessor:
    myHandlers = {}
    omsTagHash: OmsTagHash
    tradable: Tradable
    _dispatcher: Dispatcher

    def __init__(self, tradable, dispatcher):
        self.reset = None
        self.tradable = tradable
        self._dispatcher = dispatcher

    def registerOms(self, omsProcessorReset, myHnd, tagHash):
        self.reset = omsProcessorReset
        assert self.myHandlers == myHnd
        assert self.omsTagHash == tagHash

    def processExchangeMsg(self):
        '''
        Will be called from Strategy
        Generally it is a constant listener, but here we will call it from strategy.
        CALL FROM STRAT, JUST AFTER SENDING AN ORDER
        '''
        confirmNew = pickle.loads(self._dispatcher._sock.recv(4096))
        assert isinstance(confirmNew, ConfirmNew)
        self.myHandlers[OrderToStrategyMsg.ConfirmNew](ConfirmNew)

        fill = pickle.loads(self._dispatcher._sock.recv(4096))
        if fill == "No_FILL":
            return
        else:
            assert isinstance(fill, Fill)
            self.myHandlers[OrderToStrategyMsg.Fill](Fill)
