#!/usr/bin/env python
import sys
import datetime, time
import json, requests
import csv, re

from transaction_utils import TransactionQueue, TransactionConstants, TransactionRecord
from transaction_utils import Decimal
from stock_exchange_tools import Precision, get_market_price
from reports_summary import StockSummary, PortFolioSummary

class CapitalGain(TransactionConstants):
    """
    * class to calculate capital gains - both realized and holding
    * each object holds one sell transaction and the corresponding buy transaction
      the gains are calculated against those transactions
    * includes support for grandfathering Jan 31, 2018 buy price for LTCG
    """
    from stock_exchange_tools import Jan31State

    def __init__(self, sel_t, buy_t):
        self.buy_t          = buy_t
        self.sel_t          = sel_t
        decimal_zero        = Precision.DECIMAL_ZERO
        self.unit_pgain     = decimal_zero
        self.buy_value      = decimal_zero
        self.sel_value      = decimal_zero
        self.gross_gain     = decimal_zero
        self.buy_charges    = decimal_zero
        self.sel_charges    = decimal_zero
        self.net_charges    = decimal_zero
        self.net_gain       = decimal_zero
        self.gain_perc      = decimal_zero
        # tax related attributes below
        self.jan31_price    = decimal_zero
        self.tax_buy_price  = decimal_zero
        self.tax_unit_pgain = decimal_zero
        self.tax_buy_value  = decimal_zero
        self.tax_net_gain   = decimal_zero
        self.short_gain     = decimal_zero
        self.long_gain      = decimal_zero
        self.tax_long_gain  = decimal_zero
        self.gain_type      = self.SHORT_TERM

    def set_actual_gains(self):
        buy_t = self.buy_t
        sel_t = self.sel_t
        self.buy_value = Precision.three(buy_t.shares * buy_t.price)
        self.sel_value = Precision.three(sel_t.shares * sel_t.price)
        self.unit_pgain = Precision.four(sel_t.price - buy_t.price)
        self.gross_gain = Precision.three(sel_t.shares * self.unit_pgain)
        self.buy_charges = Precision.three(buy_t.brokerage + buy_t.stt + buy_t.charges)
        self.sel_charges = Precision.three(sel_t.brokerage + sel_t.stt + sel_t.charges)
        self.net_charges = Precision.three(self.sel_charges + self.buy_charges)
        self.net_gain = Precision.three(self.gross_gain - self.net_charges)
        self.gain_perc = Precision.percent(self.net_gain, self.buy_value)

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
        self.jan31_price = self.Jan31State.get_price(symbol)
        if self.jan31_price > self.buy_t.price:
            if self.sel_t.price >= self.jan31_price:
                self.tax_buy_price = self.jan31_price
            elif self.sel_t.price >= self.buy_t.price:
                self.tax_buy_price = self.sel_t.price

    def set_tax_gains(self):
        buy_t = self.buy_t
        sel_t = self.sel_t
        self.tax_buy_value = Precision.three(self.buy_t.shares * self.tax_buy_price)
        self.tax_unit_pgain = Precision.four(sel_t.price - self.tax_buy_price)
        tax_gross_gain = Precision.three(self.sel_t.shares * self.tax_unit_pgain)
        self.tax_net_gain = Precision.three(tax_gross_gain - self.net_charges)
        if self.gain_type == self.SHORT_TERM:
            self.short_gain = self.net_gain
        elif self.gain_type == self.LONG_TERM:
            self.long_gain = self.net_gain
            self.tax_long_gain = self.tax_net_gain

    def calculate(self):
        self.set_actual_gains()
        self.set_gain_type()
        self.set_tax_buy_price()
        self.set_tax_gains()

class Stock(TransactionConstants):
    """
        object to hold transactions of a particular stock
        sell transactions maintained in one queue
        buy transactions - square off and delivery are maintained in separate queues
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
        realized_t = sel_t.scale_down(realized_shares)
        remain_t = sel_t.scale_down(remain_shares)
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
            else:
                realized_t = self.realize_one(sel_t, buy_t, True)
                cg_obj = CapitalGain(sel_t, realized_t)
            self.realized_list.append(cg_obj)
        assert self.sellq.is_empty() == True
        assert self.sbuyq.is_empty() == True

    def holding_whole(self):
        if self.dbuyq.size() <= 0:
            return
        ref_date = datetime.datetime.today().date()
        market_price = get_market_price(self.symbol)
        #print self.symbol, market_price
        while self.dbuyq.is_empty() == False:
            buy_t = self.dbuyq.get()
            sel_t = buy_t.get_ref_sel_transaction(ref_date, market_price)
            cg_obj = CapitalGain(sel_t, buy_t)
            self.holding_list.append(cg_obj)
        assert self.dbuyq.is_empty() == True


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
    for transaction in map(TransactionRecord.create_obj_from_row, csv.reader(transactions_file)):
        pf.process_transaction(transaction)
    pf.process_stocks()
    pfs = PortFolioSummary(pf)
    pfs.print_summary()


if '__main__' == __name__:
    main()

