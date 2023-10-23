# saccade_project
Project submission for Saccade Capital recruitment to work with them going forward. 


# components
1. EventInjectors:
    a. Read data from 2 input files and then dispatch the ticks as 2 independent sources to the strategy (single reader of both the injectors)
    b. Can add multiple listeners to the TickListener (more than 2 possible)
2. Exchanges:
    a. Exchanges which have the ability to listen to the strategy, communicate with it
    b. Exchanges can send "ConfirmNew" and "Fill" Orders by processing the matching logic
    c. There are 2 exchanges in this module which are independent of each other and communicate with the single strategy which sends orders to both exchanges
3. Order Management System:
    a. This system can maintain the list of all orders and their states, it checks with the Risk Management System before sending any order
    b. Has the capability to read "Confirm" and "Fill" messages from the exchange, and tell the strategy to make relevant decision
    c. Has the features to send New, Can, Mod orders to the exchange, when called within the strategy
    d. This system keeps the Risk Manager informed of all the Orders sent, and Fills received
4. Risk Management System:
    a. Keeps track of all kinds of risks thresholds and current risk status of the strategy, by keeping a track
    b. maxSingleOrder, maxAtMktOrder, maxPosition, maxNetQty, maxTotalFilled, MinMaxBuyPrices, MinMaxSellPrices
    c. It communicates with Order Manager before allowing to send any orders, and after receiving any confirmations/fills from exchange
5. Kill Switch:
    a. Keeps track with Risk Manager and maintains whether trading should be allowed or not
    b. Has a refresh mechanism for Risk Manager
6. TbtProcessor:
    a. Maintains a complete container of all the instruments / tradeables in consideration
    b. Reads events, processes the Ticks and sends it to the Tick-By-Tick Orderbook in the format of New, Can, Mod, Trd ticks
7. TickByTick Orderbook:
    a. Maintains all bid and ask levels of prices and quantities
    b. Has the best bid-ask prices and quantities available, can also return quantity placed at a certain price
    c. Maintains the orderbook and keeps the checks or not breaking the basic logic of the OrderBook by using Assertion statements
    d. Handles New, Can, Mod and Trd ticks and maintains the orderbook updated by adjusting the prices/quantities
8. Instruments
    a. Has the feature of defining an Instrument, Tradable, and many other different products like equity, options, bonds, swaps, etc
    b. Has an Instrument Container which can hold multiple tradables to be fed into TbtProcessor
9. Pnl:
    a. Keeps tracks of all trades that have happened
    b. Can return open position, traded turnover, traded quantities, open pnl and closed pnl 


# module_structure
![image](https://github.com/chhabrashaleen/saccade_project/assets/61189018/b6f403a6-1d0c-43db-a311-a2ba18a41594)


