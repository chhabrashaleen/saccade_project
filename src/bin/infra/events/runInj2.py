from src.bin.infra.events.eventInjector import *
from src.config.data_cfg import inputSCS

def main():
    tradable = Tradable(InstrumentType.Equity, 2, "SCS", Decimal('0.001'), 1, True)
    port = int(input('Input Port you want to connect: '))
    eventInj = EventInject(port, tradable, inputSCS)
    eventInj.startInjection()
    eventInj.shutDown()


if __name__ == "__main__":
    main()