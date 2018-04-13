#!/usr/bin/env python
import sys
import datetime, time
import json, requests
import csv, re

from transaction_utils import TransactionQueue, TransactionConstants
from transaction_utils import TransactionRecord, Decimal
import stock_exchange_tools
from reports_summary import StockSummary, PortFolioSummary

class CapitalGain(TransactionConstants):

    JAN31_PRICE_HASH    = {}
    JAN31_NSE_FILENAME  = 'lib/NSE_20180131.csv'
    JAN31_BSE_FILENAME  = 'lib/BSE_20180131.csv'
    FIELD_DELIMITER     = ','
    SYMBOL_INDEX        = 0
    PRICE_INDEX         = 8
    IS_LOADED           = False

    @classmethod
    def set_jan31_price_hash(klass, prefix, filename):
        fp = open(filename, klass.CSV_FILE_MODE)
        fp.next()
        for line in fp:
            row = line.strip().split(klass.FIELD_DELIMITER)
            symbol, price = row[klass.SYMBOL_INDEX], row[klass.PRICE_INDEX]
            key = '%s:%s' % (prefix, symbol)
            klass.JAN31_PRICE_HASH[key] = klass.precision_4(Decimal(price))
        fp.close()

    @classmethod
    def load_31jan2018_price_hash(klass):
        if klass.IS_LOADED == False:
            klass.set_jan31_price_hash(klass.NSE_EXCH, 'lib/NSE_20180131.csv')
            klass.set_jan31_price_hash(klass.BSE_EXCH, 'lib/BSE_20180131.csv')
            klass.IS_LOADED = True

    def __init__(self, sel_t, buy_t):
        super(CapitalGain, self).__init__()
        self.buy_t          = buy_t
        self.sel_t          = sel_t
        self.unit_pgain      = self.DECIMAL_ZERO
        self.buy_value      = self.DECIMAL_ZERO
        self.sel_value      = self.DECIMAL_ZERO
        self.gross_gain     = self.DECIMAL_ZERO
        self.buy_charges    = self.DECIMAL_ZERO
        self.sel_charges    = self.DECIMAL_ZERO
        self.net_charges    = self.DECIMAL_ZERO
        self.net_gain       = self.DECIMAL_ZERO
        self.gain_perc      = self.DECIMAL_ZERO
        # tax related attributes below
        self.gain_type      = self.SHORT_TERM
        self.jan31_price    = self.DECIMAL_ZERO
        self.tax_buy_price  = self.DECIMAL_ZERO
        self.tax_unit_pgain = self.DECIMAL_ZERO
        self.tax_buy_value  = self.DECIMAL_ZERO
        self.tax_net_gain   = self.DECIMAL_ZERO
        self.short_gain     = self.DECIMAL_ZERO
        self.long_gain      = self.DECIMAL_ZERO
        self.tax_long_gain  = self.DECIMAL_ZERO

    def set_actual_gains(self):
        buy_t = self.buy_t
        sel_t = self.sel_t
        self.buy_value = self.precision_3(buy_t.shares * buy_t.price)
        self.sel_value = self.precision_3(sel_t.shares * sel_t.price)
        self.unit_pgain = self.precision_4(sel_t.price - buy_t.price)
        self.gross_gain = self.precision_3(sel_t.shares * self.unit_pgain)
        self.buy_charges = self.precision_3(buy_t.brokerage + buy_t.stt + buy_t.charges)
        self.sel_charges = self.precision_3(sel_t.brokerage + sel_t.stt + sel_t.charges)
        self.net_charges = self.precision_3(self.sel_charges + self.buy_charges)
        self.net_gain = self.precision_3(self.gross_gain - self.net_charges)
        self.gain_perc = self.precision_3((self.net_gain/self.buy_value) * Decimal('100'))

    def set_gain_type(self):
        #print self.sel_t.date, self.buy_t.date
        assert self.sel_t.date >= self.buy_t.date
        date_diff = self.sel_t.date - self.buy_t.date
        self.gain_type = self.SHORT_TERM
        if date_diff.days > self.TERM_DAYS_DIFF:
            self.gain_type = self.LONG_TERM

    def set_tax_buy_price(self):
        self.tax_buy_price = self.buy_t.price
        if self.gain_type == self.SHORT_TERM:
            return
        assert self.gain_type == self.LONG_TERM
        if self.sel_t.date < self.APR01_2018:
            return
        if self.buy_t.date > self.JAN31_2018:
            return
        symbol = self.buy_t.symbol
        self.jan31_price = self.JAN31_PRICE_HASH[symbol]
        if self.jan31_price > self.buy_t.price:
            if self.sel_t.price >= self.jan31_price:
                self.tax_buy_price = self.jan31_price
            elif self.sel_t.price >= self.buy_t.price:
                self.tax_buy_price = self.sel_t.price

    def set_tax_gains(self):
        buy_t = self.buy_t
        sel_t = self.sel_t
        self.tax_buy_value = self.precision_3(self.buy_t.shares * self.tax_buy_price)
        self.tax_unit_pgain = self.precision_4(sel_t.price - self.tax_buy_price)
        tax_gross_gain = self.precision_3(self.sel_t.shares * self.tax_unit_pgain)
        self.tax_net_gain = self.precision_3(tax_gross_gain - self.net_charges)
        if self.gain_type == self.SHORT_TERM:
            self.short_gain = self.net_gain
        elif self.gain_type == self.LONG_TERM:
            self.long_gain = self.net_gain
            self.tax_long_gain = self.tax_net_gain

    def calculate(self):
        self.__class__.load_31jan2018_price_hash()
        self.set_actual_gains()
        self.set_gain_type()
        self.set_tax_buy_price()
        self.set_tax_gains()

class Stock(TransactionConstants):
    """
        object to hold transactions of a particular stock
        sell transactions maintained in one queue
        buy transactions square off, delivery are maintained in separate queues
    """
    def __init__(self, symbol, name):
        self.symbol = symbol
        self.name   = name
        self.dbuyq  = TransactionQueue()
        self.sbuyq  = TransactionQueue()
        self.sellq  = TransactionQueue()
        self.diviq  = TransactionQueue()
        self.realized_list = []
        self.holding_list = []
        self.stock_summary = StockSummary(self)

    def put_transaction_to_queue(self, transaction, front=False):
        if transaction.trade == self.DIV:
            self.diviq.put(transaction, front)
        elif transaction.trade == self.BUY:
            if transaction.mode == self.SQR:
                self.sbuyq.put(transaction, front)
            else:
                self.dbuyq.put(transaction, front)
        elif transaction.trade == self.SEL:
            self.sellq.put(transaction, front)
        elif transaction.trade in (self.CSI, self.CSO):
            pass
        else:
            raise Exception("unknown transaction: %s" % (transaction,))

    def realize_one(self, sel_t, buy_t, swap=False):
        if swap == True:
            sel_t, buy_t = buy_t, sel_t
        remain_shares = sel_t.shares - buy_t.shares
        realized_shares = buy_t.shares
        realized_t = TransactionRecord.scale_down(sel_t, realized_shares)
        remain_t = TransactionRecord.scale_down(sel_t, remain_shares)
        self.put_transaction_to_queue(remain_t, True)
        return realized_t

    def realize_whole(self):
        buy_q_hash = {self.DEL: self.dbuyq, self.SQR: self.sbuyq}
        while self.sellq.is_empty() == False:
            sel_t = self.sellq.get()
            if sel_t.shares == 0:
                continue
            buy_t = buy_q_hash[sel_t.mode].get()
            if sel_t.shares >= buy_t.shares:
                realized_t = self.realize_one(sel_t, buy_t, False)
                cg_obj = CapitalGain(realized_t, buy_t)
                #self.realized_list.append((realized_t, buy_t))
            else:
                realized_t = self.realize_one(sel_t, buy_t, True)
                cg_obj = CapitalGain(sel_t, realized_t)
                #self.realized_list.append((sel_t, realized_t))
            self.realized_list.append(cg_obj)
        assert self.sellq.is_empty() == True
        assert self.sbuyq.is_empty() == True

    def holding_whole(self):
        if self.dbuyq.size() <= 0:
            return
        ref_date = datetime.datetime.today().date()
        market_price = self.get_market_price()
        print self.symbol, market_price
        while self.dbuyq.is_empty() == False:
            buy_t = self.dbuyq.get()
            sel_t = TransactionRecord.get_ref_sel_transaction(buy_t, ref_date, market_price)
            cg_obj = CapitalGain(sel_t, buy_t)
            self.holding_list.append(cg_obj)
        assert self.dbuyq.is_empty() == True

    def get_market_price(self):
        time.sleep(1)
        market, symbol = self.symbol.split(':')
        market_price = '0'
        if market == 'BOM':
            market = 'BSE'
            market_price = stock_exchange_tools.bseindia_scraper(market, symbol)
        elif market == 'NSE':
            market_price = stock_exchange_tools.nseindia_scraper(market, symbol)
        return self.precision_3(Decimal(market_price))


class Portfolio(object):
    """
    maintains a hash of stock ticker to stock object
    processes individual transactions from the file to create the stock hash
    transactions are stored in the respective stock object queues
    realize transactions for each stock object to find out realized, unrealized gains
    """
    def __init__(self):
        self.stock_hash = {}

    def process_transaction(self, transaction):
        if transaction.symbol[0] == '#':
            return
        ts, tn = (transaction.symbol, transaction.name)
        stock_obj = self.stock_hash.setdefault(ts, Stock(ts, tn))
        stock_obj.put_transaction_to_queue(transaction, False)

    def process_stocks(self):
        for symbol, stock_obj in self.stock_hash.iteritems():
            stock_obj.realize_whole()
            stock_obj.holding_whole()


def main():
    file_name = sys.argv[1]
    pf = Portfolio()
    transactions_file = open(file_name, TransactionConstants.CSV_FILE_MODE)
    transactions_file.next()    # skip the header
    for transaction in map(TransactionRecord.parse, csv.reader(transactions_file)):
        pf.process_transaction(transaction)
    pf.process_stocks()
    pfs = PortFolioSummary(pf)
    pfs.print_summary()


if '__main__' == __name__:
    main()

