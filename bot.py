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

# Def buy/sell simulation
    # Calculate and log amounts

# Def real buy/sell


# Calculate start time for building average
now = now()
start_time = now - res_value * slow
print("Lookback time:", dt.datetime.fromtimestamp(start_time))

# Fill in initial data from bitcoincharts.com
working_dataset = Data(res_value)
new_data, last_timestamp = dd.btccharts(start_time)
for value in new_data:
    time = value.split(',')[0]
    price = value.split(',')[1]
    working_dataset.append(time, price)

# Explicitly update dataset with last values
working_dataset.update(time, price)

for i, time in enumerate(working_dataset.time):
    print (dt.datetime.fromtimestamp(time), working_dataset.price[i])

fee = btceapi.getTradeFee(pair)
# Analytics object
act = AveragesAnalytics(res_name, fee, 2)

# Prepare object data
act.current_sum = [float(act.startsum), 0.]
act.buy_allowed = False

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
    # If able to buy and buy decision is positive
    if act.current_sum[0] > 0 \
      and act.decision('buy', fast_value, slow_value, trend):
        print("===========%s Buying for %.2f==========="
            % (dt_date(time), price))
        act.buy_sell_sim(price, 'buy', act.current_sum)

    # If able to sell and sell decision is positive
    if act.current_sum[0] > 0 \
      and act.decision('sell', fast_value, slow_value, trend):
        print("===========%s Selling for %.2f==========="
            % (dt_date(time), price))
        act.buy_sell_sim(price, 'sell', act.current_sum)
        print("Current sum is", act.current_sum[0])

    # Log operation

    sleep(10)

