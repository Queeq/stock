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
# Def buy/sell decision

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

#TODO: get fee
fee = btceapi.getTradeFee(pair)
# Analytics object
analytics = AverageAnalytics(res_name, fee, 2)

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

    print (dt_date(working_dataset.time[-1]), working_dataset.price[-1],
        working_dataset.high[-1], working_dataset.low[-1],
        "\tFast: %.2f slow: %.2f SAR: %.2f Trend: %s"
        % (mas.ma['exp'][fast][-1], mas.ma['exp'][slow][-1],
        sar.sar[-1], sar.trend[-1]))

    # Run decision function

    # Buy/sell sim or real based on config

    # Log operation
    sleep(10)

