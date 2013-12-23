import datetime as dt
import re

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

class WriteStats(object):
    def __init__(self, statsfile):
        # Erase file
        f = open(statsfile, 'w')
        f.close()

        # Open to append
        self.f = open(statsfile, 'a')

    def append(self, analytics_obj, res_name, ma, pair):
        data = """\
==== %s %s %s ====
Pair profitability:	%.2f%%
Biggest win:		%.2f%%
Biggest loss:		%.2f%%
Sum on won trades:	%.2f
Sum on lost trades:	%.2f
Number of wins:		%d
Number of losts:	%d
Max consecutive wins:	%d
Max consecutive losts:	%d
Max consecutive profit:	%.2f%%
Max consecutive loss:	%.2f%%

""" % (
            res_name, ma, pair,
            analytics_obj.profit[ma][pair[0]][pair[1]],
            analytics_obj.biggest_win[ma][pair],
            analytics_obj.biggest_loss[ma][pair],
            analytics_obj.won_trades_sum[ma][pair],
            analytics_obj.lost_trades_sum[ma][pair],
            analytics_obj.won_trades_num[ma][pair],
            analytics_obj.lost_trades_num[ma][pair],
            analytics_obj.max_consecutive_wins[ma][pair],
            analytics_obj.max_consecutive_losts[ma][pair],
            analytics_obj.max_consecutive_profit[ma][pair],
            analytics_obj.max_consecutive_loss[ma][pair]
            )

        self.f.write(data)

    def __del__(self):
        self.f.close()


# Return current time timestamp
def now():
    return int(dt.datetime.now().strftime('%s'))

# Return timestamp of datetime object
def dt_timestamp(dt_obj):
    return int(dt_obj.strftime('%s'))

# Return date object from timestamp
def dt_date(timestamp):
    return dt.datetime.fromtimestamp(timestamp)

# Function to convert resolution from word to seconds
# Returns dict like { 5m: 300, ... }
def resolutions_convert(res_string):
    resolutions_conf = {}
    regex = re.compile("(\d+)([mh])")

    for res in res_string.split(','):
        m = regex.match(res)
        amount = int(m.group(1)) # number
        suffix = m.group(2) # mins or hours
        if suffix == 'm':
            multiplier = 60
        elif suffix == 'h':
            multiplier = 60*60
        resolutions_conf[res] = amount * multiplier

    return resolutions_conf
