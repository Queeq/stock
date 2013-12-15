#!/usr/bin/python3

import argparse
import os
import sys
import urllib.request
import datetime as dt

"""
This script gets the last data from bitcoincharts.com
and appends it to existing CSV file from the same site
"""

aparser = argparse.ArgumentParser()
aparser.add_argument('-f', dest='datafile_path', required=True, help='CSV file to work on')
args = aparser.parse_args()

# Determine latest timestamp in our datafile
with open(args.datafile_path, 'rb') as f:
    offset = 100 # How much bytes to read from the end of file
    f.seek(0, os.SEEK_END)
    fsize = f.tell()
    if fsize == 0:
        print("Error: file is empty.")
        sys.exit(1)

    # Read and split into lines
    f.seek(-1*offset, os.SEEK_END)
    raw_data = f.read().decode()
    lines = raw_data.split('\n')
    # Get last line
    last_line = lines[-1]
    last_timestamp = int(last_line.split(',')[0])
    print("Last available point is at %s" % dt.datetime.fromtimestamp(last_timestamp))

# Get latest data from Bitcoincharts
btcc_data = urllib.request.urlopen("http://api.bitcoincharts.com/v1/trades.csv?symbol=btceUSD&start=%d" % last_timestamp)

# Form data list of all lines except the first one
new_data = btcc_data.read().decode().split('\n')[1:]
newest_timestamp = int(new_data[-1].split(',')[0])

# Append data to file
print("Appending %s lines to file. Last point is at %s" % (len(new_data), dt.datetime.fromtimestamp(newest_timestamp)))

with open(args.datafile_path, 'a') as f:
    for line in new_data:
        f.write("\n"+line)

