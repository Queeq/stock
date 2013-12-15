#!/usr/bin/python3

import sys
import argparse

import time as t
import csv
import datetime as dt

import numpy as np
import array
import itertools

import matplotlib as mp
mp.use('agg')
import matplotlib.pyplot as plt

# Classifying resolutions for stock data
resolutions_conf = {'30m': 30*60, '1h': 60*60, '2h': 2*60*60}

# Classifying average periods
av_periods = range(1,50)

# List of all available period pairs
av_pairs = list(itertools.combinations(av_periods, 2))


# Parse arguments
aparser = argparse.ArgumentParser()
aparser.add_argument('-i', '--input', dest='datafile_path', required=True, help='CSV file to get data from')
aparser.add_argument('-f', '--fee', dest='fee', help='Stock fee. Default: 0.002')
aparser.add_argument('-p', '--period', dest='timedelta', nargs=2, metavar=('INTEGER', '{d|w|m|y}'), help='From what time ago to start analysis. Value with day/week/month/year suffix')
aparser.add_argument('-s', '--start', dest='startdate', help='Date to start analysis from. Format: dd.mm.yy')
aparser.add_argument('-e', '--end', dest='enddate', help='Date to finish analysis at. Format: dd.mm.yy')
aparser.add_argument('--no-plot', dest='do_plot', action='store_false', help='Do not draw plots, just show text stats')
aparser.set_defaults(do_plot=True, fee=0.002)
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


# Progress calculation and printing
class Progress(object):
    def __init__(self, maximum):
        self.maximum = maximum
        self.last_percent = 0
    def show(self, current):
        percent = round(current/self.maximum * 100)
        if percent > self.last_percent:
            self.last_percent = percent
            print ("%d%% complete \r" % percent, end="")
            if percent == 100:
                print ("")


# Make a time:price class
class Data(object):
    """
    Structure:

    L0: Separate object for every resolution (eg. 5m, 1h, etc.)
        Usually objects are put in a dictionary with corresponding keys

    L1: Array #1: time
        Array #2: price

    L2: Elements of the array

    """
    def __init__(self, resolution = 0):
        self.time = array.array('I') # Unsigned int - 2 bytes
        self.price = array.array('d') # Double - 8 bytes. Setting 'f' (4 bytes float) leads to incorrect values!

        self.resolution = resolution # Accepting only closing price of such intervals (e.g. 5 min, 30 min, 1h), in seconds
        self.append_tries = 0

    def set_interval_end(self, time):
        # If resolution 0 - let every line be written
        if self.resolution == 0:
            self.interval_end = -1
        else:
            # Calculate next interval end based on received current time
            self.interval_end = (time//self.resolution + 1) * self.resolution

    # Fill empty intervals with previous data
    def fill_empty_intervals(self, time, to_write):
        # How many intervals missed?
        intervals_missed = (time - self.interval_end) // self.resolution

        if intervals_missed > 0:
            for i in range (1, intervals_missed + 1):
                self.time.append(self.interval_end + self.resolution * i)
                self.price.append(to_write['price'])

    def append(self, time, price):
        time = int(time)
        price = float(price)
        index = len(self.time)

        # Put first line into dictionary and calculate first interval end
        if self.append_tries == 0:
            self.last_line = {'time': time, 'price': price}
            self.set_interval_end(time)

        self.append_tries += 1

        # What to write
        if self.resolution == 0:
            # Write current values
            to_write = {'time': time, 'price': price}
        else:
            # Write previous values
            to_write = self.last_line

        # If interval end passed - assign values from previous read
        if time - self.interval_end >= 0:
            self.time.append(to_write['time'])
            self.price.append(to_write['price'])

            # Do not fill empty intervals for generic data
            if time - self.interval_end > self.resolution and self.resolution != 0:
                self.fill_empty_intervals(time, to_write)

            self.last_line = {'time': time, 'price': price}
            self.set_interval_end(time)

        else:
            self.last_line = {'time': time, 'price': price}

    def read(self, index):
        output = {'time': self.time[index], 'price': self.price[index]}
        return output

# Moving averages class
class MovingAverages(object):
    """
    Structure:

    L0: Separate object for every resolution (5m, 1h, etc.)
        Usually objects are put in a dictionary with corresponding keys

    L1: Dictionary of MA types as keys (simple or exponential)
        self.ma{type}
        Values are dictionaries of L2

    L2: Dictionary of periods from global list av_periods as keys
        self.ma{type}{period}
        Values are arrays of averages. Len = len of dataobject of given resolution

    L3: Elements of the array

    """
    def __init__(self, res):
        self.resolution = res

        self.ma = {'simple': {}, 'exp': {}}

        # Price array.array from data object of same resolution
        data = discrete_data[self.resolution].price
        datalen = len(data)

        '''
        For all periods, create lists of arrays
        and fill these arrays with calculated averages
        '''

        prog = Progress(max(av_periods))
        for period in av_periods:
            # Create dictionaries of arrays
            self.ma['simple'][period] = array.array('d') # Simple moving average
            self.ma['exp'][period] = array.array('d') # Exponential moving average

            weights_sma = np.ones(period)
            weights_ema = np.exp(np.linspace(-1., 0., period))

            weights_sma /= weights_sma.sum()
            weights_ema /= weights_ema.sum()

            # Add data from numpy convolution result list to arrays
            self.ma['simple'][period].extend(np.convolve(data, weights_sma, mode='full')[:datalen])
            self.ma['exp'][period].extend(np.convolve(data, weights_ema, mode='full')[:datalen])

            # Cut first elements as they are out of range
            self.ma['simple'][period] = self.ma['simple'][period][max(av_periods):]
            self.ma['exp'][period] = self.ma['exp'][period][max(av_periods):]

            prog.show(period)

        # Cut first elements for Data obj of given resolution as well
        discrete_data[self.resolution].time = discrete_data[self.resolution].time[max(av_periods):]
        discrete_data[self.resolution].price = discrete_data[self.resolution].price[max(av_periods):]


class AveragesAnalytics(object):
    """
    Structure:

    L0: Separate object for every resolution (5m, 1h, etc.)
        Usually objects are put in a dictionary with corresponding keys
        Includes multilevel dictionaries of the following data:

        L1: self.minimum_profit - MA type minimum profit (percent)
        L1: self.average_profit - MA type average profit (percent)
        L1: self.maximum_profit - MA type maximum profit (percent)
        L2: self.current_sum - list of (<currency1_amount>, <currency2_amount>)
        L2: self.end_sum - last value of <currency1_amount>
        L2: self.profit - percent, end_sum/startsum
        L2: self.transactions - value of number of successful buys+sells

    L1: MA type as a key (simple or exponential)
        Value is a dictionary of L2 or a variable of L1
        <name>{ma_type}{av_pair_list}

    L2: Dictionary of average periods pair list as a key (eg. (1, 2), (1, 3) etc.)
        Values are actual data
        <name>{ma_type}{av_pair_list}
        or
        <name>{ma_type}[fast_period][slow_period] - for end_sum and profit

    """
    def __init__(self, res):
        self.resolution = res
        self.fee = float(args.fee)
        self.startsum = 100
        self.avdata = av[res]
        self.data = discrete_data[res]

        self.ma_variants = ('simple', 'exp')
        self.current_sum = {}
        self.end_sum = {}
        self.profit = {}
        self.transactions = {}

        self.minimum_profit = {}
        self.average_profit = {}
        self.maximum_profit = {}

        # For both SMA and EMA variants, do...
        for ma in self.ma_variants:

            print ("Calculating profits for %s '%s'" % (self.resolution, ma))
            # Current amount of currencies of each pair
            self.current_sum[ma] = {}
            # Init empty masked 2-dimensional numpy arrays for end_sum and profit
            dimension = max(av_periods)+1
            self.end_sum[ma] = np.ma.empty((dimension, dimension))
            self.end_sum[ma][:] = np.NaN
            self.profit[ma] = np.ma.empty((dimension, dimension))
            self.profit[ma][:] = np.NaN
            # Dictionary of number of transactions of each pair
            self.transactions[ma] = {}

            self.minimum_profit[ma] = 0
            self.average_profit[ma] = 0
            self.maximum_profit[ma] = 0

            prog = Progress(len(av_pairs))

            # Slow and fast MA intersections. All combinations
            for pair_number, av_pair in enumerate(av_pairs):
                # Set fast and slow averages periods
                fast_period, slow_period = av_pair

                av_datalength = len(self.avdata.ma[ma][fast_period])
                self.current_sum[ma][av_pair] = [float(self.startsum), 0.]
                self.transactions[ma][av_pair] = 0

                # Iterate over averages data to find intersections
                for index in range(av_datalength):
                    fast = self.avdata.ma[ma][fast_period][index]
                    slow = self.avdata.ma[ma][slow_period][index]

                    # If able to buy - look for fast going above slow
                    if self.current_sum[ma][av_pair][0] > 0 and fast > slow:
                        # Get price from data object
                        price = self.data.price[index]
                        # Simulate buy
                        self.buy_sell_sim(price, 'buy', self.current_sum[ma][av_pair])
                        self.transactions[ma][av_pair] += 1
                    # Else, if able to sell - look for fast going below slow
                    elif self.current_sum[ma][av_pair][1] > 0 and fast < slow:
                        # Get price from data object
                        price = self.data.price[index]
                        # Simulate sell
                        self.buy_sell_sim(price, 'sell', self.current_sum[ma][av_pair])
                        # Set end sum to current sum in case this is the last sell
                        self.end_sum[ma][fast_period][slow_period] = self.current_sum[ma][av_pair][0]
                        self.transactions[ma][av_pair] += 1

                # When buying simulation for this pair is finished - record end_sum and profit
                self.profit[ma][fast_period][slow_period] = (self.end_sum[ma][fast_period][slow_period] - self.startsum) * 100 / self.startsum
                prog.show(pair_number)
                # end intra-pair simulation loop

            # end av_pairs loop

            # Mask NaN values to exclude from calculations
            self.end_sum[ma] = np.ma.masked_invalid(self.end_sum[ma])
            self.profit[ma] = np.ma.masked_invalid(self.profit[ma])
            self.minimum_profit[ma] = self.profit[ma].min()
            self.average_profit[ma] = self.profit[ma].mean()
            self.maximum_profit[ma] = self.profit[ma].max()

            print ("%s %s profit/lost: min %.2f%% av %.2f%% max %.2f%%" % (self.resolution, ma, self.minimum_profit[ma], self.average_profit[ma], self.maximum_profit[ma]))

        # end ma type loop


    # Simulate buying or selling all
    def buy_sell_sim(self, price, action, current_sum):
        if action == 'buy':
            # Actually buy
            current_sum[1] = current_sum[0] / price
            # Minus fee
            current_sum[1] -= current_sum[1] * self.fee
            #print ("Buy %.4f btc for %.4f usd; %.2f" % (current_sum[1], current_sum[0], price))
            # Set currency 1 amount to 0
            current_sum[0] = 0

        if action == 'sell':
            # Actually sell
            current_sum[0] = current_sum[1] * price
            # Minus fee
            current_sum[0] -= current_sum[0] * self.fee
            #print ("Sell %.4f btc for %.4f usd; %.2f" % (current_sum[1], current_sum[0], price))
            # Set currency 2 amount to 0
            current_sum[1] = 0


"""
Main program start
"""

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

print ('Data read')

actual_endtime = full_data.time[-1]
if actual_endtime < endtime:
    print ("Last data point is at %s" % dt.datetime.fromtimestamp(actual_endtime))
    timeperiod_str = "%s - %s" % (dt.datetime.fromtimestamp(starttime), dt.datetime.fromtimestamp(actual_endtime))

print ("\n")

# Get full_data arrays' size
fulldata_len = len(full_data.time)

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
    av[res_name] = MovingAverages(res_name)

#p_res="1h"
## Testing data
#for index, time in enumerate(discrete_data[p_res].time):
#    if index < 20 or index > len(discrete_data[p_res].time) - 20:
#        print (index, time, "p: %.2f\tav_3: %.2f\tav_5: %.2f" % (discrete_data[p_res].price[index], av[p_res].ma['simple'][3][index], av[p_res].ma['simple'][5][index]))

analytics = {}
for res_name in resolutions_conf.keys():
    analytics[res_name] = AveragesAnalytics(res_name)
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
            max_profit = analytics[res_name].maximum_profit[ma_type]

            plt.subplot2grid((plot_rows, plot_columns), (0, type_index))
            plt.title("%s %s %s\nMin: %.2f Max: %.2f" % (timeperiod_str, res_name, ma_type, min_profit, max_profit))
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
        plt.savefig('plot-%s.png' % res_name, dpi=dpi, bbox_inches='tight')
        del fig

else:
    print ("Plotting skipped")

