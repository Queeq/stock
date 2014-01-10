#!/usr/bin/python3

import argparse
import configparser
import datetime as dt
from time import sleep
from sys import exit
from os import path

import btceapi

from common.basic import *
from common import datadownload as dd
from analysis.analysis import *

# Get configuration from ini
config = configparser.ConfigParser()
config.read('config.ini')
fast = int(config['bot']['fast'])
slow = int(config['bot']['slow'])
stop_loss = float(config['bot']['stop_loss'])
res_name = config['bot']['resolution']
res_value = resolutions_convert(res_name)[res_name]
trading_sum = float(config['bot']['trading_sum'])

# Parse arguments
aparser = argparse.ArgumentParser()
aparser.add_argument('-r', '--real', dest='real_trading', action="store_true", help='Activate real trading')
aparser.set_defaults(real_trading=False)
args = aparser.parse_args()

real_trading = args.real_trading
keyfile = "keyfile"
keyfile = path.abspath(keyfile)

# One connection for everything
conn = btceapi.common.BTCEConnection()

pair = 'btc_usd'
fee = btceapi.getTradeFee(pair, connection=conn)
# API returns fee in percent. Get absolute value
fee /= 100

print("Current fee is", fee)
print("Trading", pair, "pair")
print("EMA", fast, slow)
print("Tick size", res_name)

class ActionTimeout(object):
    """
    Don't instantly act after signal is generated.
    Wait 1/2 of period from last signal change to
    confirm it and actually do what we are supposed to do.
    """
    def __init__(self, action, res_value):
        self.action = action
        self.res_value = res_value
        self.trigger_at = float("inf")

    def update(self, signal):
        # Reset trigger if signal changed
        if signal != self.action and self.trigger_at != float("inf"):
            self.trigger_at = float("inf")
            print("Reset", self.action, "timeout")
        # If timer was reset and signal is ours now - set new trigger time
        elif signal == self.action and self.trigger_at == float("inf"):
            self.trigger_at = now() + self.res_value/2
            print("Set", self.action, "timeout to", dt_date(self.trigger_at))


# TODO:
    # Compare trading sum with total available sum
    # Compare and update analytics object (give warning on different values)
class Trading(object):
    """
    Class to check account status and act upon that
    """
    def __init__(self, keyfile):
        self.handler = btceapi.KeyHandler(keyfile)
        try:
            self.key = self.handler.getKeys()[0]
        except IndexError:
            print("Error: something's wrong with keyfile. Looks like it's empty")
            exit(1)

        self.api = btceapi.TradeAPI(self.key, self.handler)
        self.update_balance()

        # Simplest possible check. Rely upon API for everything else
        if self.usd == 0 and self.btc == 0:
            print("Not enough funds for real trading. Activating simulation")
            real_trading = False

        # Trade all available money on the following condition
        if trading_sum >= self.usd or trading_sum <= 0:
            print("Trading all available money of %s!" % self.usd)
            self.trade_all = True
        else:
            self.trade_all = False

    def update_balance(self):
        self.acc_info = self.api.getInfo()

        self.usd = self.acc_info.balance_usd
        self.btc = self.acc_info.balance_btc

    def min_amount(self, trade_type, price=0):
        """
        Returns minimum amount allowed to trade
        """
        btc_min_amount = 0.01
        if trade_type == "buy":
            usd_min_amount = btc_min_amount * price
            print("Min amount", usd_min_amount, "USD")
            return usd_min_amount
        else:
            print("Min amount", btc_min_amount, "BTC")
            return btc_min_amount

    def prices(self):
        """
        Returns tuple of closest ask/bid prices (ask, bid)
        """
        asks, bids = btceapi.getDepth(pair)
        return (asks[0][0], bids[0][0])

    def lowest_ask(self):
        return self.prices()[0]

    def highest_bid(self):
        return self.prices()[0]

    def buy(self):
        if self.trade_all:
            trading_sum = self.usd

        hi_bid = self.highest_bid()
        # Buy for sure - set buy price 0.1% higher than highest bid
        #price = hi_bid + hi_bid*0.001
        price = hi_bid - 100
        # Calculate amounts based on trading sum
        sum_to_buy = trading_sum/price
        # Minus fee
        sum_to_buy -= sum_to_buy * fee
        print(dt_date(now()), "Placing BUY order: %f BTC for %f USD. Price %f"
            % (sum_to_buy, trading_sum, price))
        result = self.api.trade(pair, "buy", price, sum_to_buy, conn)
        print(result.received, result.remains, result.order_id)
        self.update_balance()

    def sell(self):
        lo_ask = self.lowest_ask()
        # Sell for sure - set sell price 0.1% lower than lowest ask
        #price = lo_ask - lo_ask*0.001
        price = lo_ask + 100

        # Calculate amounts
        if self.trade_all:
            sum_to_sell = self.btc
        else:
            sum_to_sell = trading_sum/price
            if sum_to_sell > self.btc:
                sum_to_sell = self.btc

        # Minus fee
        sum_to_sell -= sum_to_sell * fee
        print(dt_date(now()), "Placing BUY order: %f BTC for %f USD. Price %f"
            % (sum_to_sell, trading_sum, price))
        result = self.api.trade(pair, "sell", price, sum_to_sell, conn)
        print(result.received, result.remains, result.order_id)
        self.update_balance()


if real_trading:
    # Activate trading object
    trade = Trading(keyfile)
    trade.prices()

# Calculate start time for building average
start_time = now() - res_value * slow
#print("Lookback time:", dt.datetime.fromtimestamp(start_time))

# Fill in initial data from bitcoincharts.com
working_dataset = Data(res_value)
new_data, last_timestamp = dd.btccharts(start_time)
for value in new_data:
    time = value.split(',')[0]
    price = value.split(',')[1]
    working_dataset.append(time, price)

# Explicitly update dataset with last values
working_dataset.update(time, price)

#for i, time in enumerate(working_dataset.time):
#    print (dt.datetime.fromtimestamp(time), working_dataset.price[i])

# Analytics object
act = AveragesAnalytics(res_name, fee, 2)

# Prepare object data
act.current_sum = [float(act.startsum), 0.]
act.buy_allowed = False

# Activate timeout objects
buy_timeout = ActionTimeout("buy", res_value)
sell_timeout = ActionTimeout("sell", res_value)

# Loop
while True:
    try:
        # Get latest trades and update DB
        last_trades = btceapi.getTradeHistory(pair, count=100, connection=conn)
    except Exception as ex:
        # Ignore all exceptions, just print them out and keep it on.
        #print(dt_date(now()), "getTradeHistory failed. Skipping actions and reopening connection.\nThe error was:", ex)
        # Try to open new connection
        conn = btceapi.common.BTCEConnection()
    else:
        for t in last_trades:
            time = dt_timestamp(t.date)
            working_dataset.update(time, t.price)

        # Calculate averages based on working dataset
        mas = MovingAverages(working_dataset, (fast, slow), realtime=True)
        # Calculate SAR for working dataset
        sar = SAR(working_dataset)

        fast_value = mas.ma['exp'][fast][-1]
        slow_value = mas.ma['exp'][slow][-1]
        trend = sar.trend[-1]
        price = working_dataset.price[-1]
        time = working_dataset.time[-1]

        '''
        print (dt_date(time), price,
            working_dataset.high[-1], working_dataset.low[-1],
            "\tFast: %.2f slow: %.2f SAR: %.2f Trend: %s"
            % (fast_value, slow_value, sar.sar[-1], trend))
        '''

        # If buy signal
        if act.decision('buy', fast_value, slow_value, trend):
            # Calculate timeouts
            buy_timeout.update("buy")
            sell_timeout.update("buy")

            # If able to buy and buy timeout passed - act
            # Simulation part
            if act.current_sum[0] > 0 \
              and now() > buy_timeout.trigger_at:
                print("===========%s Simulation buying for %.2f==========="
                    % (dt_date(time), price))
                act.buy_sell_sim(price, 'buy', act.current_sum)

            # Real part
            if real_trading and trade.usd > trade.min_amount("buy", price) \
              and now() > buy_timeout.trigger_at:
                trade.buy()
            # TODO: Calculate and log amounts

        # If sell signal
        if act.decision('sell', fast_value, slow_value, trend):
            # Calculate timeouts
            buy_timeout.update("sell")
            sell_timeout.update("sell")

            # If able to sell and sell timeout passed - act
            if act.current_sum[1] > 0 \
              and now() > sell_timeout.trigger_at:
                print("===========%s Simulation selling for %.2f==========="
                    % (dt_date(time), price))
                act.buy_sell_sim(price, 'sell', act.current_sum)
                # TODO: Calculate and log amounts
                print("Current sum is", act.current_sum[0])

            # Real part
            if real_trading and trade.btc > trade.min_amount("sell") \
              and now() > sell_timeout.trigger_at:
                trade.sell()

    # End main try-else block

    sleep(10)

