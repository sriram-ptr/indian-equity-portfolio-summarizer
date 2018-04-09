#!/usr/bin/env python
import sys
import csv

from transaction_utils import TransactionQueue, TransactionConstants
from transaction_utils import TransactionRecord, Decimal
from reports_summary import StockSummary, PortFolioSummary

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
                self.realized_list.append((realized_t, buy_t))
            else:
                realized_t = self.realize_one(sel_t, buy_t, True)
                self.realized_list.append((sel_t, realized_t))
        assert self.sellq.is_empty() == True
        assert self.sbuyq.is_empty() == True

class CapitalGains(TransactionConstants):

    def __init__(self):
        self.jan31_price_hash = {}

    def set_jan31_price_hash(self, prefix, filename):
        fp = open(filename, 'rUb')
        fp.next()
        for line in fp:
            row = line.strip().split(',')
            symbol, price = row[0], row[8]
            key = '%s:%s' % (prefix, symbol)
            self.jan31_price_hash[key] = self.precision_4(Decimal(price))
        fp.close()

    def grandfather_jan31_price(self, symbol, buy_tp, sel_tp):
        new_bp = buy_tp
        jan31_p = self.jan31_price_hash[symbol]
        if jan31_p > buy_tp:
            if sel_tp >= jan31_p:
                new_bp = jan31_p
            elif sel_tp < jan31_p and sel_tp >= buy_tp:
                new_bp = sel_tp
        return new_bp, jan31_p

    def classify_term(self, buy_td, sel_td):
        assert sel_td >= buy_td
        date_diff = sel_td - buy_td
        if date_diff.days > 365:
            return 'long'
        return 'short'

    def main(self):
        self.set_jan31_price_hash('NSE', 'lib/NSE_20180131.csv')
        self.set_jan31_price_hash('BOM', 'lib/BSE_20180131.csv')


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


def main():
    file_name = sys.argv[1]
    pf = Portfolio()
    transactions_file = open(file_name, "rUb")
    transactions_file.next()    # skip the header
    for transaction in map(TransactionRecord.parse, csv.reader(transactions_file)):
        pf.process_transaction(transaction)
    pf.process_stocks()
    cg = CapitalGains()
    cg.main()
    pfs = PortFolioSummary(pf, cg)
    pfs.print_summary()


if '__main__' == __name__:
    main()

