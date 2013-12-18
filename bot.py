#!/usr/bin/python3

import configparser
import datetime as dt
from time import sleep

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

for i, time in enumerate(working_dataset.time):
    print (dt.datetime.fromtimestamp(time), working_dataset.price[i])
# Loop
while True:
    # Get latest trades and update DB

    # Calculate averages

    # Run decision function

    # Buy/sell sim or real based on config

    # Log operation
    sleep(10)

