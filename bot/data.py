class SharedData(object):
    def __init__(self, trading_sum, real_trading, connection):
        self.trading_sum = trading_sum
        self.real_trading = real_trading
        self.conn = connection
