#!/usr/bin/python3

import argparse

# Own package imports
from common.basic import *

"""

Script to find trades that are out of order in CSV file
Commonly seen in bitcoincharts.com files (at least btceUSD.csv)
Then file can be fixed by running
sort -t ',' -k 1 -o <output_file> <input_file>

"""

aparser = argparse.ArgumentParser()
aparser.add_argument('-f', dest='datafile_path', required=True, help='CSV file to work on')
args = aparser.parse_args()

with open(args.datafile_path, 'r') as f:
    # Buffer list
    buf = []
    # Put first line
    buf.append(f.readline())
    for i, line in enumerate(f):
       # Put current line into buffer
       buf.append(line)

       prev_timestamp = float(buf[0].split(",")[0])
       cur_timestamp = float(buf[1].split(",")[0])

       # Timestamps can be only ascending
       if prev_timestamp > cur_timestamp:
           print("%s detected around %s" % (dt_date(prev_timestamp), dt_date(cur_timestamp)))

       del buf[0]
       if i % 100000 == 0:
           print("Line: %s" % i)

