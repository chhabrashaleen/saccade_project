### saccade_project
Project submission for Saccade Capital recruitment to work with them going forward. 


### components

# EventInjectors:
1. Read data from 2 input files and then dispatch the ticks as 2 independent sources to the strategy (single reader of both the injectors)
2. Can add multiple listeners to the TickListener (more than 2 possible)

# Exchanges:
1. Exchanges which have the ability to listen to the strategy, communicate with it
2. Exchanges can send "ConfirmNew" and "Fill" Orders by processing the matching logic
3. There are 2 exchanges in this module which are independent of each other and communicate with the single strategy which sends orders to both exchanges

# Order Management System:
1. This system can maintain the list of all orders and their states, it checks with the Risk Management System before sending any order
2. Has the capability to read "Confirm" and "Fill" messages from the exchange, and tell the strategy to make relevant decision
3. Has the features to send New, Can, Mod orders to the exchange, when called within the strategy
4. This system keeps the Risk Manager informed of all the Orders sent, and Fills received

# Risk Management System:
1. Keeps track of all kinds of risks thresholds and current risk status of the strategy, by keeping a track
2. maxSingleOrder, maxAtMktOrder, maxPosition, maxNetQty, maxTotalFilled, MinMaxBuyPrices, MinMaxSellPrices
3. It communicates with Order Manager before allowing to send any orders, and after receiving any confirmations/fills from exchange

# Kill Switch:
1. Keeps track with Risk Manager and maintains whether trading should be allowed or not
2. Has a refresh mechanism for Risk Manager

# TbtProcessor:
1. Maintains a complete container of all the instruments / tradeables in consideration
2. Reads events, processes the Ticks and sends it to the Tick-By-Tick Orderbook in the format of New, Can, Mod, Trd ticks

# TickByTick Orderbook:
1. Maintains all bid and ask levels of prices and quantities
2. Has the best bid-ask prices and quantities available, can also return quantity placed at a certain price
3. Maintains the orderbook and keeps the checks or not breaking the basic logic of the OrderBook by using Assertion statements
4. Handles New, Can, Mod and Trd ticks and maintains the orderbook updated by adjusting the prices/quantities

# Instruments
1. Has the feature of defining an Instrument, Tradable, and many other different products like equity, options, bonds, swaps, etc
2. Has an Instrument Container which can hold multiple tradables to be fed into TbtProcessor

# Pnl:
1. Keeps tracks of all trades that have happened
2. Can return open position, traded turnover, traded quantities, open pnl and closed pnl 


# module_structure
![image](https://github.com/chhabrashaleen/saccade_project/assets/61189018/b6f403a6-1d0c-43db-a311-a2ba18a41594)


