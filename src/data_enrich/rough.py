# '''Assuming that a new tick (for the traded order) comes before a trade tick'''
# if tData.exchangeOrderNumberBuy > 0:
#     '''this was a hit on the buy side.
#     Someone has sold by hitting at bestBid hence the new tick modifies the bestAsk'''
#     self.handleNew(TbtTickNewCan(tData.header, tData.exchangeOrderNumberBuy, tData.tradedPrice, -tData.tradedQuantity))
# elif tData.exchangeOrderNumberSell > 0:
#     '''this was a hit on the ask side.
#     Someone has bought by hitting at bestAsk hence the new tick modifies the bestBid'''
#     self.handleNew(TbtTickNewCan(tData.header, tData.exchangeOrderNumberSell, tData.tradedPrice, tData.tradedQuantity))