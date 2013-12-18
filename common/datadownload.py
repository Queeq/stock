import urllib.request
import datetime as dt
import time as t

# Own package imports
from . import basic as b

def btccharts(from_time):
    newest_timestamp = 0
    new_data = []
    # Fetch data while most recent data is not older than 1 minute
    # due to current limitation for bitcoincharts being 20000 rows at once
    while b.now() - newest_timestamp > 60:
        print("Getting data from bitcoincharts.com")
        # Get latest data from Bitcoincharts
        btcc_data = urllib.request.urlopen("http://api.bitcoincharts.com/v1/trades.csv?symbol=btceUSD&start=%d" % from_time)
        # Form data list of all lines except the first one
        new_data.extend(btcc_data.read().decode().split('\n')[1:])
        newest_timestamp = int(new_data[-1].split(',')[0])
        from_time = newest_timestamp
        print("Got lines, last timestamp %s" % dt.datetime.fromtimestamp(newest_timestamp))
        t.sleep(0.1)

    return (new_data, newest_timestamp)
