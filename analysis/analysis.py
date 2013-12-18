import numpy as np
import array

from common.basic import *

# Time:price class
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

    L2: Dictionary of periods from av_periods list as keys
        self.ma{type}{period}
        Values are arrays of averages. Len = len of dataobject of given resolution

    L3: Elements of the array

    """
    def __init__(self, res, data_obj, av_periods):
        self.resolution = res

        # Price array.array from data object of same resolution
        data = data_obj.price
        datalen = len(data)

        self.ma = {'simple': {}, 'exp': {}}

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
        data_obj.time = data_obj.time[max(av_periods):]
        data_obj.price = data_obj.price[max(av_periods):]


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
    def __init__(self, res, fee, av_obj, data_obj, av_periods, av_pairs):
        self.resolution = res
        self.fee = float(fee)
        self.startsum = 100
        self.avdata = av_obj
        self.data = data_obj

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

