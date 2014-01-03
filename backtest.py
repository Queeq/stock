#!/usr/bin/python3

import sys
import argparse
import configparser

import time as t
import csv
import datetime as dt

import numpy as np
import itertools

import matplotlib as mp
mp.use('agg')
import matplotlib.pyplot as plt

from analysis.analysis import *
from common.basic import *

# Get configuration from ini
config = configparser.ConfigParser()
config.read('config.ini')
resolutions = config['backtest']['resolutions']
av_range = config['backtest']['average_periods']

# Dictionary for resolutions name:seconds
resolutions_conf = resolutions_convert(resolutions)

# Parse average periods
av_min_period, av_max_period = map(int, av_range.split('-'))
av_periods = range(av_min_period, av_max_period)

# List of all available period pairs
av_pairs = list(itertools.combinations(av_periods, 2))

# Parse arguments
aparser = argparse.ArgumentParser()
aparser.add_argument('-i', '--input', dest='datafile_path', required=True, help='CSV file to get data from')
aparser.add_argument('-f', '--fee', dest='fee', help='Stock fee. Default: 0.002')
aparser.add_argument('-p', '--period', dest='timedelta', nargs=2, metavar=('INTEGER', '{d|w|m|y}'), help='From what time ago to start analysis. Value with day/week/month/year suffix')
aparser.add_argument('-s', '--start', dest='startdate', help='Date to start analysis from. Format: dd.mm.yy')
aparser.add_argument('-e', '--end', dest='enddate', help='Date to finish analysis at. Format: dd.mm.yy')
aparser.add_argument('-a', '--algorithm', dest='algorithm', help="""Algorithm to use.
1: MA crossings (default).
2: MA crossings with simple SAR (buy on crossing, sell on crossing + SAR trend down).
3: MA crossings with thresholds (see analysis/analysis.py decision()).""")
aparser.add_argument('--no-plot', dest='do_plot', action='store_false', help='Do not draw plots, just show text stats')
aparser.set_defaults(do_plot=True, fee=0.002, algorithm=1)
args = aparser.parse_args()

now = int(dt.datetime.now().strftime('%s'))

# Decode symbol from period argument
period_decode = {'d': 24*3600, 'w': 7*24*3600, 'm': 30*24*3600, 'y': 365*24*3600}

# Time period
if args.timedelta:
    starttime = now - int(args.timedelta[0]) * period_decode[args.timedelta[1]]
elif args.startdate:
    start = dt.datetime.strptime(args.startdate, '%d.%m.%y')
    starttime = int(start.strftime('%s'))
else:
    starttime = 0

if args.enddate:
    end = dt.datetime.strptime(args.enddate, '%d.%m.%y')
    endtime = int(end.strftime('%s'))
else:
    endtime = now


# Open file and determine human-readable start-end interval
datafile = open(args.datafile_path, newline='')
timeperiod_str = "%s - %s" % (dt.datetime.fromtimestamp(starttime), dt.datetime.fromtimestamp(endtime))

# Read all data from csv file to data class
rowcount = 0
full_data = Data()

# Import data from n earlier periods too to calculate correct averages for the start of interval
lookback_time = starttime - (max(resolutions_conf.values()) * max(av_periods))

print ("Importing data for %s" % timeperiod_str)
print ("Lookback time: %s" % dt.datetime.fromtimestamp(lookback_time))

for row in csv.reader(datafile):
    if lookback_time < int(row[0]):
        full_data.append(row[0], row[1])
        rowcount += 1
        if rowcount % 100000 == 0:
            print("Row: %s" % rowcount)
        if int(row[0]) >= endtime:
            break

datafile.close()

# Get full_data arrays' size and check it against rowcount of the source file
fulldata_len = len(full_data.time)
assert rowcount == fulldata_len == len(full_data.price)

print ('Data read')

actual_endtime = full_data.time[-1]
if actual_endtime < endtime:
    print ("Last data point is at %s" % dt.datetime.fromtimestamp(actual_endtime))
    timeperiod_str = "%s - %s" % (dt.datetime.fromtimestamp(starttime), dt.datetime.fromtimestamp(actual_endtime))

print ("\n")

# Init dictionary for data objects
discrete_data = {}

for res_name, res_value in resolutions_conf.items():
    print ("Filling %s data object" % res_name)

    # Create data objects for every configured resolution and put them in a dict
    discrete_data[res_name] = Data(res_value)

    prog = Progress(fulldata_len)

    # Determine lookback time for current resolution
    lookback_time = starttime - (res_value * max(av_periods))
    print ("Lookback time for %s is %s" % (res_name, dt.datetime.fromtimestamp(lookback_time)))

    # Fill in discrete data objects
    for index in range(fulldata_len):
        if full_data.read(index)['time'] >= lookback_time:
            discrete_data[res_name].append(full_data.read(index)['time'], full_data.read(index)['price'])
        prog.show(index)

# No need to keep all data in memory now
del full_data


av = {}
for res_name in resolutions_conf.keys():
    print ("Computing %s averages object" % res_name)
    # Create averages objects for every configured resolution and put them in a dict
    av[res_name] = MovingAverages(discrete_data[res_name], av_periods)

    # Check lenghts
    assert len(av[res_name].ma['simple'][av_min_period+1]) == len(av[res_name].ma['simple'][av_max_period-1]) == \
        len(av[res_name].ma['exp'][av_min_period+1]) == len(av[res_name].ma['exp'][av_max_period-1]) == \
        len(discrete_data[res_name].time) == len(discrete_data[res_name].price) == \
        len(discrete_data[res_name].high) == len(discrete_data[res_name].low)

SARs = {}
for res_name in resolutions_conf.keys():
    print ("Computing %s SAR object" % res_name)
    # Dictionary for SAR objects of different resolutions
    SARs[res_name] = SAR(discrete_data[res_name])

    assert len(SARs[res_name].trend) == len(SARs[res_name].sar) == len(discrete_data[res_name].time)

"""
p_res="1h"
# Testing data
for index, time in enumerate(discrete_data[p_res].time):
    if index < 20 or index > len(discrete_data[p_res].time) - 20:
        print (index, dt.datetime.fromtimestamp(time), "p: %.2f\ts_3: %.2f\te_3: %.2f" %
            (discrete_data[p_res].price[index],
            av[p_res].ma['simple'][3][index],
            av[p_res].ma['exp'][3][index]))
"""

analytics = {}
for res_name in resolutions_conf.keys():
    analytics[res_name] = AveragesAnalytics(res_name, args.fee, args.algorithm)
    analytics[res_name].backtest(av[res_name], discrete_data[res_name], av_periods, av_pairs, SARs[res_name])
    print ("")

if args.do_plot:

    # Find absolute profit min and max
    abs_profit_min = min(min(val) for val in [profit_dict.values() for profit_dict in [an_obj.minimum_profit for an_obj in analytics.values()]])
    abs_profit_max = max(max(val) for val in [profit_dict.values() for profit_dict in [an_obj.maximum_profit for an_obj in analytics.values()]])

    # Separate figure with one column for every resolution
    plot_columns = 2
    # One row for SMA, second for EMA
    plot_rows = 1

    # Calculate dpi and font size based on grapsh size
    dpi = max(av_periods) * 8
    fontsize = 800 / dpi

    for res_index, (res_name, res_value) in enumerate(resolutions_conf.items()):

        fig = plt.figure(figsize=(10 * plot_columns, 6 * plot_rows))
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        for type_index, ma_type in enumerate(('simple', 'exp')):
            print ("Building %s '%s' subplot" % (res_name, ma_type))
            plot_data = analytics[res_name].profit[ma_type]
            plot_mask = np.ma.getmaskarray(plot_data)
            min_profit = analytics[res_name].minimum_profit[ma_type]
            av_profit = analytics[res_name].average_profit[ma_type]
            max_profit = analytics[res_name].maximum_profit[ma_type]

            plt.subplot2grid((plot_rows, plot_columns), (0, type_index))
            plt.title("%s\n%s %s. Algorithm #%s\nMin: %.2f Av: %.2f Max: %.2f" % (timeperiod_str, res_name, ma_type, args.algorithm, min_profit, av_profit, max_profit))
            for (x, y), value in np.ndenumerate(plot_data):
                if plot_mask[x, y] == False:
                    plt.text(x + 0.5, y + 0.5, '%.2f%%\n(%d, %d)' % (value, x, y), horizontalalignment='center', verticalalignment='center', fontsize=fontsize)

            heatmap = plt.pcolormesh(plot_data.T, cmap=plt.cm.RdYlGn, vmin=abs_profit_min, vmax=abs_profit_max)

            plt.colorbar(heatmap)
            plt.gca().autoscale_view('tight')
            # Turn off axis
            plt.gca().axison = False

        # Free up memory of plotted object
        del av[res_name]

        print ("Composing figure for %s resolution" % res_name)
        plt.tight_layout()
        plt.savefig('plot-%s %s.png' % (res_name, timeperiod_str), dpi=dpi, bbox_inches='tight')
        del fig

else:
    print ("Plotting skipped")

# Print stats to file
for res_name in resolutions_conf.keys():
    wr_stats = WriteStats('stats-%s %s.txt' % (res_name, timeperiod_str))

    for ma in ('simple', 'exp'):
        print("Writing stats for", res_name, ma)
        prog = Progress(len(av_pairs))

        for i, pair in enumerate(av_pairs):
            wr_stats.append(analytics[res_name], res_name, ma, pair)
            prog.show(i)

    del wr_stats

