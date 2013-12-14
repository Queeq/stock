from btceapi import btceapi
import configparser

config = configparser.ConfigParser()
config.read('btceapi/config.ini')

api_key = config['DEFAULT']['api_key']
api_sec = config['DEFAULT']['api_secret']

api = btceapi.api(api_key, api_sec)

print(api.TradeHistory(tfrom=0, tcount=10, tfrom_id=0, tend_id=99999999999, torder='ASC', tsince=0, tend=99999999999999, tpair='btc_usd'))
