from src.bin.infra.exchanges.exchange import *

def main():
    tradable = Tradable(InstrumentType.Equity, 2, "SCS", Decimal('0.001'), 1, True)
    # port = int(input('Input Port you want to connect: '))
    '''Assiging a pre fixed value for ease'''
    port = 9000
    exchange = Exchange(tradable, port)
    exchange.start()
    exchange.listen()

if __name__ == "__main__":
    main()