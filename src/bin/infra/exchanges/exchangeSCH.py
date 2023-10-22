from src.bin.infra.exchanges.exchange import *

def main():
    tradable = Tradable(InstrumentType.Equity, 1, "SCH", Decimal('0.01'), 1, True)
    # port = int(input('Input Port you want to connect: '))
    '''Assiging a pre fixed value for ease'''
    port = 8080
    exchange = Exchange(tradable, port)
    exchange.start()
    exchange.listen()

if __name__ == "__main__":
    main()