#!/usr/bin/env python
import csv
import copy
from transaction_utils import TransactionQueue, TransactionConstants
from transaction_utils import TransactionRecord
from reports_summary import StockSummary, PortFolioSummary

class Stock(TransactionConstants):

    def __init__(self, symbol, name):
        self.symbol = symbol
        self.name   = name
        self.dbuyq  = TransactionQueue()
        self.sbuyq  = TransactionQueue()
        self.sellq  = TransactionQueue()
        self.diviq  = TransactionQueue()
        self._dbuyq = None
        self._sbuyq = None
        self._diviq = None
        # reports
        self.realized_list = []
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
        else:
            pass
            #raise Exception("unknown transaction trade: %s" % (transaction,))

    def preserve_transactions(self):
        self._dbuyq = copy.deepcopy(self.dbuyq)
        self._sbuyq = copy.deepcopy(self.sbuyq)
        self._sellq = copy.deepcopy(self.sellq)

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
                self.realized_list.append((realized_t, buy_t))
            else:
                realized_t = self.realize_one(sel_t, buy_t, True)
                self.realized_list.append((sel_t, realized_t))
        assert self.sellq.is_empty() == True
        assert self.sbuyq.is_empty() == True

    def get_realized_buy_value(self):
        sum1 = sum([buy_t.value for buy_t in self._dbuyq])
        sum2 = sum([buy_t.value for buy_t in self._sbuyq])
        return -1*(sum1+sum2)

    def get_holding_value(self):
        sum1 = sum([buy_t.value for buy_t in self.dbuyq])
        return -1*sum1

    def get_realized_sell_value(self):
        return sum([sel_t.value for sel_t in self.sellq])


class Portfolio(object):

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
            stock_obj.preserve_transactions()
            stock_obj.realize_whole()

import sys
file_name = sys.argv[1]
pf = Portfolio()
transactions_file = open(file_name, "rUb")
transactions_file.next()    # skip the header
for transaction in map(TransactionRecord.parse, csv.reader(transactions_file)):
    pf.process_transaction(transaction)
pf.process_stocks()
pfs = PortFolioSummary(pf)
pfs.print_summary()
