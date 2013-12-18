#!/usr/bin/python3

import configparser
import datetime as dt

from common.basic import *

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


# Build database for last trades to calculate on
    # Get data from bicoincharts.com and then those trades which are in between from BTC-e API

# Calculate start time for building average
now = now()
start_time = now - res_value * slow
print(dt.datetime.fromtimestamp(start_time))

# Loop

    # Get latest trades and update DB

    # Calculate averages

    # Run decision function

    # Buy/sell sim or real based on config

    # Log operation

