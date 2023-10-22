from src.bin.infra.events.eventInjector import *
from src.config.data_cfg import inputSCH

def main():
    tradable = Tradable(InstrumentType.Equity, 1, "SCH", Decimal('0.01'), 1, True)
    port = int(input('Input Port you want to connect: '))
    eventInj = EventInject(port, tradable, inputSCH)
    eventInj.startInjection()
    eventInj.shutDown()


if __name__ == "__main__":
    main()