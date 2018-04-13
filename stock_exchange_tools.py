import time
import re
import json
import requests

def bseindia_scraper(market, symbol):
    # getquote_SV1.js
    #url = "https://www.bseindia.com/SiteCache/1D/GetQuoteData.aspx?Type=EQ&text=%s" % symbol
    #rsp = requests.get(url)
    #next_urls = re.findall(' href\s*=\s*[\'"](.*?)[\'"]', rsp.content)
    #assert len(next_urls) == 1
    #url = next_urls[0]
    assert market == 'BSE'
    url = "https://www.bseindia.com/stock-share-price/SiteCache/IrBackupStockReach.aspx?scripcode=%s&DebtFlag=C" % symbol
    rsp = requests.get(url)
    price_list = re.findall('class\s*=\s*[\'"]tbmaingreen[\'"]\>(.*?)\</td\>', rsp.content) # green = positive
    if len(price_list) == 0:
        price_list = re.findall('class\s*=\s*[\'"]tbmainred[\'"]\>(.*?)\</td\>', rsp.content) # red = negative
    assert len(price_list) == 1
    return price_list[0]

def nseindia_scraper(market, symbol):
    assert market == 'NSE'
    url = 'https://www.nseindia.com/live_market/dynaContent/live_watch/get_quote/GetQuote.jsp?symbol=%s&illiquid=0&smeFlag=0&itpFlag=0' % symbol
    headers = {
        'Accept' : '*/*',
        'Accept-Language' : 'en-US,en;q=0.5',
        'Host': 'nseindia.com',
        'Referer': "https://www.nseindia.com/live_market/dynaContent/live_watch/get_quote/GetQuote.jsp?symbol=COALINDIA.NS&illiquid=0&smeFlag=0&itpFlag=0",
        'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
        'X-Requested-With': 'XMLHttpRequest'
    }
    rsp = requests.get(url, headers=headers)
    price_list = re.findall('(\{\s*[\'"]futLink[^\r]*)\r\n', rsp.content)
    assert len(price_list) == 1
    price_dict = json.loads(price_list[0])
    return price_dict['data'][0]['lastPrice']


def googlefinance(market, symbol):
    """ deprecated, not working anymore """
    url = "https://finance.google.com/finance?q=%s:%s&output=json" % (market, symbol)
    return '0'

def alphavantage(market, symbol):

    def try_api_call(url, params):
        retries = 0
        rsp = None
        fin_data = {}
        while retries < 6:
            retries += 1
            time.sleep(2)
            rsp = requests.get(url, params=params)
            fin_data = {}
            if rsp.status_code != 200:
                print 'retry = %s, status = %s, params = %s' % (retries, rsp.status_code, params)
                continue
            fin_data = json.loads(rsp.content)
            if "Error Message" in fin_data:
                print 'retry = %s, status = %s, params = %s, data = %s' % (retries, rsp.status_code, params, fin_data)
                continue
            break
        return rsp, fin_data

        time.sleep(1)
        if market == 'BOM':
            market = 'BSE'
        market_price_str = '0'
        url = "https://www.alphavantage.co/query"
        interval = '60min'
        params = { 'apikey': '417VIWXIWW71MYDT', 'function': 'TIME_SERIES_INTRADAY', 'market': market, 'symbol': symbol, 'interval': interval }
        #url = "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&apikey=417VIWXIWW71MYDT&market=%s&symbol=%s&interval=60min" % (market, symbol)
        rsp, fin_data = try_api_call(url, params)
        try:
            last_refr = fin_data["Meta Data"]["3. Last Refreshed"]
            market_price_str = fin_data["Time Series (%s)" % interval][last_refr]["4. close"]
        except KeyError:
            print 'ERROR %s after RETRIES: %s' % (rsp.status_code, rsp.content)
        return market_price_str


