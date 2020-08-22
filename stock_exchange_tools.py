#!/usr/bin/env python

import time
import re
import json
import requests
import csv23
from decimal import Decimal, getcontext, ROUND_HALF_UP
getcontext().rounding = ROUND_HALF_UP

class Precision(object):
    """
    Avoid floating point arithmetic errors and get required precision accuracy
    This is possible using the Decimal class
    This class is just a wrapper over constants and functions for namespace
    """
    # rounding off

    DECIMAL_ZERO = Decimal(0) 
    DECIMAL_TEN  = Decimal(10)
    DECIMAL_HUND = Decimal(100)
    ROUND_2 = DECIMAL_TEN ** -2
    ROUND_3 = DECIMAL_TEN ** -3
    ROUND_4 = DECIMAL_TEN ** -4

    # various precision methods for numbers

    @classmethod
    def integer(cls, dec_x):
        return dec_x.quantize(cls.DECIMAL_TEN, rounding=ROUND_HALF_UP)

    @classmethod
    def four(cls, dec_x):
        return dec_x.quantize(cls.ROUND_4, rounding=ROUND_HALF_UP)

    @classmethod
    def three(cls, dec_x):
        return dec_x.quantize(cls.ROUND_3, rounding=ROUND_HALF_UP)

    @classmethod
    def two(cls, dec_x):
        return dec_x.quantize(cls.ROUND_2, rounding=ROUND_HALF_UP)

    @classmethod
    def percent(cls, num, den):
        return cls.three((num * cls.DECIMAL_HUND)/den)


class Jan31State(object):
    """
    * tax on LTCG announced in Budget 2018
    * Purchase price of existing Long Term holdings to be grandfathered using Jan 31 price of the stock
    * this class will load the Jan 31 price for NSE and BSE stocks
    * the attributes are at the class level, object creation not expected but will continue to work
    """
    CSV_FILE_READ_MODE  = "rUb"
    JAN31_PRICE_HASH    = {}
    JAN31_NSE_FILENAME  = 'lib/NSE_20180131.csv'
    JAN31_BSE_FILENAME  = 'lib/BSE_20180131.csv'
    SYMBOL_INDEX        = 0
    PRICE_INDEX         = 8
    IS_LOADED           = False

    @classmethod
    def get_symbol_price(cls, row):
        return row[cls.SYMBOL_INDEX], row[cls.PRICE_INDEX]

    @classmethod
    def set_jan31_price_hash(cls, filename):
        with csv23.open_reader(filename) as fp:
            next(fp)
            stock_price_hash = {
                symbol: Precision.four(Decimal(price))
                for (symbol, price) in map(cls.get_symbol_price, fp)
            }
        cls.JAN31_PRICE_HASH.update(stock_price_hash)

    @classmethod
    def load_31jan2018_price_hash(cls):
        if cls.IS_LOADED == False:
            cls.set_jan31_price_hash(cls.JAN31_NSE_FILENAME)
            cls.set_jan31_price_hash(cls.JAN31_BSE_FILENAME)
            cls.IS_LOADED = True

    @classmethod
    def get_price(cls, symbol):
        cls.load_31jan2018_price_hash()
        return cls.JAN31_PRICE_HASH[symbol]

    def __init__(self):
        self.load_31jan2018_price_hash()


class StockExchange(object):
    def __init__(self):
        self.url = ''
        self.headers = {}

    def scrape(self, symbol):
        url = self.url % symbol
        rsp = requests.get(url, headers=self.headers)
        return rsp


class NSE(StockExchange):
    def __init__(self):
        super(NSE, self).__init__()
        self.url = 'https://www.nseindia.com/live_market/dynaContent/live_watch/get_quote/GetQuote.jsp?symbol=%s&illiquid=0&smeFlag=0&itpFlag=0'
        self.url = 'https://www1.nseindia.com/live_market/dynaContent/live_watch/get_quote/GetQuote.jsp?symbol=%s'
        self.any_re = re.compile(r'\{<div\s+id="responseDiv"\s+style="display:none">\s+(\{.*?\{.*?\}.*?\})')
        self.any_re = re.compile(r'<div\s+id="responseDiv"\s+style="display:none">\s+(\{.*?\{.*?\}.*?\})')
        self.headers = {
            'Host': 'www1.nseindia.com', 
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            #'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            #'Referer': self.url % 'INFY',
            #'X-Requested-With': 'XMLHttpRequest'
        }

    def get_market_price(self, symbol):
        rsp = self.scrape(symbol)
        price_list = self.any_re.findall(rsp.content.decode())
        assert len(price_list) == 1
        price_dict = json.loads(price_list[0])
        return price_dict['data'][0]['lastPrice']

class BSE(StockExchange):
    def __init__(self):
        super(BSE, self).__init__()
        self.url = "https://api.bseindia.com/BseIndiaAPI/api/StockReachGraph/w?scripcode=%s&flag=0&fromdate=&todate=&seriesid="
        self.url = "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w?Debtflag=&scripcode=%s&seriesid="
        self.headers = {
                'Host': 'api.bseindia.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                #'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
                'TE': 'Trailers'
        }

    def get_market_price(self, symbol):
        rsp = self.scrape(symbol)
        json_rsp = json.loads(rsp.content)
        price_str = json_rsp["CurrRate"]["LTP"]
        assert price_str is not None and price_str != ""
        return price_str.strip()

nse = NSE()
bse = BSE()

def get_market_price(stock_ticker):
    market, symbol = stock_ticker.split(':')
    obj = {'NSE': nse, 'BSE': bse}[market]
    price_str = obj.get_market_price(symbol)
    return Precision.three(Decimal(price_str))

#print(get_market_price('NSE:GICRE'))
#print(get_market_price('BSE:500285'))
