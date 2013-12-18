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


# Return current time timestamp
def now():
    return int(dt.datetime.now().strftime('%s'))

# Return timestamp of datetime object
def dt_timestamp(dt_obj):
    return int(dt_obj.strftime('%s'))

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
