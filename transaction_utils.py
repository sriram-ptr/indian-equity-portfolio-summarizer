#!/usr/bin/env python

"""
* Transaction based utilities are implemented in this module
* Includes a queue to hold transactions, constants involved in a transaction
* Author: Sriram Ponnusamy, feel free to use and distribute
"""
import math
from collections import namedtuple
from dateutil.parser import parse as date_parse
from decimal import Decimal, getcontext, ROUND_HALF_UP
getcontext().rounding = ROUND_HALF_UP

class TransactionQueue(object):

    _KEY = 0

    def __init__(self):
        self.items = []

    def is_empty(self):
        return len(self.items) == self._KEY

    def size(self):
        return len(self.items)

    def put(self, item, front):
        if front == True:
            self.items.insert(self._KEY, item)
        else:
            self.items.append(item)

    def get(self):
        return self.items.pop(self._KEY)

    def __iter__(self):
        return self.items.__iter__()


class TransactionConstants(object):

    BUY = 'Buy'
    SEL = 'Sell'
    DIV = 'Dividend'
    SQR = 'sqr'
    DEL = 'del'
    # rounding off
    DECIMAL_TEN = Decimal('10')
    ROUND_2 = DECIMAL_TEN ** -2
    ROUND_3 = DECIMAL_TEN ** -3
    ROUND_4 = DECIMAL_TEN ** -4

    @classmethod
    def precision_int(klass, dec_x):
        return dec_x.quantize(klass.DECIMAL_TEN, rounding=ROUND_HALF_UP)

    @classmethod
    def precision_4(klass, dec_x):
        return dec_x.quantize(klass.ROUND_4, rounding=ROUND_HALF_UP)

    @classmethod
    def precision_3(klass, dec_x):
        return dec_x.quantize(klass.ROUND_3, rounding=ROUND_HALF_UP)

    @classmethod
    def precision_2(klass, dec_x):
        return dec_x.quantize(klass.ROUND_2, rounding=ROUND_HALF_UP)

TRANSACTION_FIELDS = [
    'symbol', 'name', 'trade', 'date', 'shares', 'price', 'value',
    'brokerage', 'stt', 'charges', 'receivable', 'mode'
]

_TransactionRecord = namedtuple('_TransactionRecord', TRANSACTION_FIELDS)
class TransactionRecord(_TransactionRecord, TransactionConstants):

    @classmethod
    def parse(klass, row):
        row = list(row)
        row[3] = date_parse(row[3]).date()
        row[4:-1] = map(Decimal, row[4:-1])
        for i in (4,):
            row[i] = klass.precision_int(row[i])
        for i in (5,6,7,8,9,10):
            row[i] = klass.precision_3(row[i])
        return klass(*row)

    @classmethod
    def scale_down(klass, transaction, rem_shares):
        dec_rem_shares = Decimal(rem_shares)
        t = list(transaction)   # transaction has all numbers as Decimal objects
        diff_ratio = dec_rem_shares/t[4]
        t[4] = klass.precision_int(dec_rem_shares)
        t[8] = klass.precision_3(diff_ratio * t[8])
        #t[8] = klass.precision_int(new_stt)
        for i in (6,7,9):
            t[i] = klass.precision_3(diff_ratio * t[i])
        t[10] = klass.precision_3(t[6] - sum(t[7:10]))
        return klass(*t)

    def validate(self):
        assert self.symbol and self.name
        assert self.trade in (self.BUY, self.SEL, self.DIV)
        assert self.mode in (self.SQR, self.DEL)
        if self.trade == self.DIV:
            return
        assert self.shares > 0
        assert self.price > 0
        assert self.brokerage > 0
        assert self.stt >= 0
        assert self.charges > 0

