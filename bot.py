#!/usr/bin/python3

import configparser
import datetime as dt
from time import sleep
from sys import exit

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

pair = 'btc_usd'
fee = btceapi.getTradeFee(pair)
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
        if signal != self.action:
            self.trigger_at = float("inf")
            print("Reset", self.action, "timeout")
        # If timer was reset and signal is ours now - set new trigger time
        elif signal == self.action and self.trigger_at == float("inf"):
            self.trigger_at = now() + self.res_value/2
            print("Set", self.action, "timeout to", dt_date(self.trigger_at))


# TODO:
# Def real buy/sell
    # Get account info
    # Check if enough USD
    # Compare and update analytics object (give warning on different values)


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
    # Get latest trades and update DB
    last_trades = btceapi.getTradeHistory(pair, count=100)
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

    print (dt_date(time), price,
        working_dataset.high[-1], working_dataset.low[-1],
        "\tFast: %.2f slow: %.2f SAR: %.2f Trend: %s"
        % (fast_value, slow_value, sar.sar[-1], trend))

    #### Simulation ####
    # If buy signal
    if act.decision('buy', fast_value, slow_value, trend):
        # Calculate timeouts
        buy_timeout.update("buy")
        sell_timeout.update("buy")

        # If able to buy and buy timeout passed - act
        if act.current_sum[0] > 0 \
          and now() > buy_timeout.trigger_at:
            print("===========%s Buying for %.2f==========="
                % (dt_date(time), price))
            act.buy_sell_sim(price, 'buy', act.current_sum)
        # TODO: Calculate and log amounts

    # If sell signal
    if act.decision('sell', fast_value, slow_value, trend):
        # Calculate timeouts
        buy_timeout.update("sell")
        sell_timeout.update("sell")

        # If able to sell and sell timeout passed - act
        if act.current_sum[1] > 0 \
          and now() > sell_timeout.trigger_at:
            print("===========%s Selling for %.2f==========="
                % (dt_date(time), price))
            act.buy_sell_sim(price, 'sell', act.current_sum)
            # TODO: Calculate and log amounts
            print("Current sum is", act.current_sum[0])

    sleep(10)

