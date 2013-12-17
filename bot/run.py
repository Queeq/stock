#!/usr/bin/python3

import os.path
import configparser

# Get parent dir path
top_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
# Get config path
config_path = os.path.join(top_dir, "config.ini")

# Get configuration from ini
config = configparser.ConfigParser()
config.read(config_path)
fast = int(config['bot']['fast'])
slow = int(config['bot']['slow'])
stop_loss = float(config['bot']['stop_loss'])
resolution = config['bot']['resolution']

print(fast, slow, stop_loss, resolution)

# Def buy/sell decision

# Def buy/sell simulation
    # Calculate and log amounts

# Def real buy/sell


# Build database for last trades to calculate on
    # Get data from bicoincharts.com and then those trades which are in between from BTC-e API

# Loop

    # Get latest trades and update DB

    # Calculate averages

    # Run decision function

    # Buy/sell sim or real based on config

    # Log operation

