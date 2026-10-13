
from datatypes import Ticker


TRAINING_UNIVERSE: list[Ticker] = [
    # ETFs
    Ticker(ticker='SPY'),
    Ticker(ticker='QQQ'),

    # TECH GIANTS
    Ticker(ticker='AAPL'),
    Ticker(ticker='GOOGL'),
    Ticker(ticker='NVDA'),
    Ticker(ticker='AMD'),
    Ticker(ticker='TSM'),

    # CONSUMPTION
    Ticker(ticker='KO'),
    Ticker(ticker='PEP'),
    Ticker(ticker='BIMBOA.MX'),

    # DEFENSIVE CONSUMPTION
    Ticker(ticker='FEMSAUBD.MX'),

    # RETAIL
    Ticker(ticker='WALMEX.MX'),

    # E-COMMERCE
    Ticker(ticker='AMZN'),
    Ticker(ticker='MELI'),

    # TOURISM
    Ticker(ticker='ABNB'),

    # ENERGY
    Ticker(ticker='XOM'),
    Ticker(ticker='CVX'),

    # AUTOMOTIVE
    Ticker(ticker='TSLA'),
    Ticker(ticker='F'),
    Ticker(ticker='GM'),

    # AEROSPACE
    Ticker(ticker='BA'),

    # FINANCE
    Ticker(ticker='JPM'),
    Ticker(ticker='BAC'),

    # ENTERTAINMENT
    Ticker(ticker='DIS'),
    Ticker(ticker='NFLX'),

    # INDUSTRIAL
    Ticker(ticker='CAT'),
    Ticker(ticker='GE'),

    # HEALTHCARE
    Ticker(ticker='JNJ'),
    Ticker(ticker='LLY'),
    Ticker(ticker='UNH'),

    # CRYPTO
    Ticker(ticker='COIN'),

    # VOLATILITY
    Ticker(ticker='NKE'),
    Ticker(ticker='RKLB'),
    Ticker(ticker='RXRX'),
]
