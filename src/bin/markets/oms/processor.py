from src.bin.markets.instruments import *
from src.bin.markets.tbt_datafeed.tick_print_orderbook import *
from src.bin.markets.oms.obstatus import *

class DispatchHeader:
    msgCode: int


class OmsTagHash:
    instrumentId: int
    omgTag: int
    algoId: int


class OmsProcessor:

    myHandlers: dict
    omsTagHash: OmsTagHash

    def __init__(self):

        self.reset = None


    def registerOms(self, omsProcessorReset, myHnd, tagHash):
        self.reset = omsProcessorReset
        self.myHandlers = myHnd
        self.omsTagHash = tagHash

    def processOrders(self, obs: OBStatus):

        pass


