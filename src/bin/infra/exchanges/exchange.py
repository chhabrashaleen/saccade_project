'''This is the exchange which listens to oms orders and sends confirmations to oms processor'''

import socket
import pickle
import time

from src.bin.markets.oms.obstatus import *
from src.bin.markets.oms.messages import *
import src.config.logger as log
import time
logger = log.logger

class Exchange:
    _tdb: Tradable
    _host = '127.0.0.1'
    _port: int
    _connected = False
    _toListen: int
    _totalClient: int
    _connections = []
    _allOS = {}

    def __init__(self, tdb, port, totalClient=1, toListen=1):
        self._tdb = tdb
        self._port = port
        self._toListen = toListen
        self._totalClient = totalClient
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._order = None
        self._obStatus = None

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self._host, self._port))
        self.server_socket.listen(self._toListen)  # Listen for up to 5 incoming connections
        logger.info("Server listening on %s:%s", self._host, self._port)
        for i in range(self._totalClient):
            conn, addr = self.server_socket.accept()
            logger.info("Accepted Connection from: %s", addr)
            self._connections.append(conn)

    def sendDataPack(self, packet):
        try:
            if not packet:
                logger.warn("%s Nothing to dispatch, no data received.", packet)
            else:
                logger.info("Exchange:%s Sending packet:%s", self._tdb.instrumentId, packet)
                pickledData = pickle.dumps(packet)
                self._connections[0].send(pickledData)
        except:
            logger.warning("Packet sending not working. Sleeping for some time...")

    def listen(self):
        while True:
            try:
                assert len(self._connections) == 1
                data = (self._obStatus, self._orderState) = pickle.loads(self._connections[0].recv(4096))
                logger.info("Exchange:%s Received OBStatus:%s", self._tdb.instrumentId, self._obStatus)
                if not data:
                    self.server_socket.close()
                    break
                self.processAllOrders(self._obStatus, self._orderState)
            except KeyboardInterrupt:
                self.server_socket.close()
                logger.warn("Listener closed, by keyboard interruption")

    def processAllOrders(self, obs: OBStatus, orderState: OrderState):
        '''
        Assuming that all orders will be of absolute Qty=1 and will get filled or remain open, removing the
        possibility of partial fills, and there will be only one Fill at a time.
        If the current order is a Market Order, it will be filled, and we will keep
        the remaining open limit orders unchecked. All these cases can also be handled in current infra.
        '''
        orderState.isConfirmed = True
        assert not orderState.isFinished and not orderState.isCancelSent
        self._allOS[orderState.order.orderNumber] = orderState

        '''Strategy also Sending a confirmNew message'''
        confirmNew = self.createConfirmNew(obs, orderState)
        logger.info("Exchange:%s prepared ConfirmNew:%s", self._tdb.instrumentId, confirmNew)

        time.sleep(1 / 1000)
        self.sendDataPack(confirmNew)

        gotFill = False
        '''Checking for Fills'''
        for ordNum, ordState in self._allOS.items():
            assert isinstance(ordState, OrderState)
            if ordState.isConfirmed and not ordState.isFinished and not ordState.isCancelSent:
                if orderState.desiredQty > 0:
                    if obs.bestAsk <= orderState.desiredPrice:
                        orderState.isFinished = True
                        gotFill = True
                        fill = self.createFill(obs, orderState)
                        '''Filling at best ask'''
                        fill.price = obs.bestAsk
                        '''Sending the fill message'''
                        logger.info("Exchange:%s prepared Fill:%s", self._tdb.instrumentId, fill)
                        self.sendDataPack(fill)
                        break
                elif orderState.desiredQty < 0:
                    if obs.bestBid >= orderState.desiredPrice:
                        orderState.isFinished = True
                        gotFill = True
                        fill = self.createFill(obs, orderState)
                        '''Filling at best bid'''
                        fill.price = obs.bestBid
                        '''Sending the fill message'''
                        logger.info("Exchange:%s prepared Fill:%s", self._tdb.instrumentId, fill)
                        self.sendDataPack(fill)
                        break
        if not gotFill:
            logger.info("Exchange:%s NO_FILL", self._tdb.instrumentId)
            self.sendDataPack("NO_FILL")

    def createFill(self, obs: OBStatus, orderState: OrderState) -> Fill:
        fill = Fill()
        fill.orderManagerId = orderState.order.orderManagerId
        fill.orderNumber = orderState.order.orderNumber
        fill.instrumentId = self._tdb.instrumentId
        '''Assuming that the fill happens at the mid price. This thing is handled above'''
        fill.price = (obs.bestAsk + obs.bestBid)/2
        fill.qty = orderState.desiredQty
        fill.eventTime = obs.header.eventTime
        return fill

    def createConfirmNew(self, obs: OBStatus, orderState: OrderState) -> ConfirmNew:
        confirm = ConfirmNew()
        confirm.orderNumber = orderState.order.orderNumber
        confirm.orderManagerId = orderState.order.orderManagerId
        confirm.eventTime = obs.header.eventTime
        return confirm
