#!/usr/bin/env python

"""
* Transaction based utilities are implemented in this module
* Includes a queue to hold transactions, constants involved in a transaction
* Author: Sriram Ponnusamy, feel free to use and distribute
"""
import math, datetime
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
    """
    defines all constants possible in a transaction
    """
    # trade types
    BUY = 'Buy'
    SEL = 'Sell'
    DIV = 'Dividend'
    CSI = 'CashIn'
    CSO = 'CashOut'
    TRADE_TYPES = [BUY, SEL, DIV, CSI, CSO]

    # modes
    SQR = 'sqr'
    DEL = 'del'
    CAS = 'cash'
    MODES = [SQR, DEL, CAS]

    # rounding off
    DEC_TEN = Decimal('10')
    ROUND_2 = DEC_TEN ** -2
    ROUND_3 = DEC_TEN ** -3
    ROUND_4 = DEC_TEN ** -4

    # sale date from when LTCG becomes taxable
    APR01_2018 = datetime.datetime(2018, 4, 1).date()

    # various precision methods for numbers

    @classmethod
    def precision_int(klass, dec_x):
        return dec_x.quantize(klass.DEC_TEN, rounding=ROUND_HALF_UP)

    @classmethod
    def precision_4(klass, dec_x):
        return dec_x.quantize(klass.ROUND_4, rounding=ROUND_HALF_UP)

    @classmethod
    def precision_3(klass, dec_x):
        return dec_x.quantize(klass.ROUND_3, rounding=ROUND_HALF_UP)

    @classmethod
    def precision_2(klass, dec_x):
        return dec_x.quantize(klass.ROUND_2, rounding=ROUND_HALF_UP)

    # transaction csv file columns
    SYMBOL_F        = 'symbol'
    NAME_F          = 'name'
    TRADE_F         = 'trade'
    DATE_F          = 'date'
    SHARES_F        = 'shares'
    PRICE_F         = 'price'
    VALUE_F         = 'value'
    BROKERAGE_F     = 'brokerage'
    STT_F           = 'stt'
    CHARGES_F       = 'charges'
    RECEIVABLE_F   = 'receivable'
    MODE_F          = 'mode'

    # order of transaction fields
    TRANSACTION_FIELDS = [
        SYMBOL_F, NAME_F, TRADE_F, DATE_F, SHARES_F, PRICE_F, VALUE_F,
        BROKERAGE_F, STT_F, CHARGES_F, RECEIVABLE_F, MODE_F
    ]
    # fields to be modified for types
    MOD_DATE_LIST   = [DATE_F]
    MOD_INT_LIST    = [SHARES_F]
    MOD_PR3_LIST    = [PRICE_F, VALUE_F, BROKERAGE_F, STT_F, CHARGES_F, RECEIVABLE_F]



class TransactionRecord(TransactionConstants):

    _TransactionRecord = namedtuple('_TransactionRecord', TransactionConstants.TRANSACTION_FIELDS)

    @classmethod
    def parse(klass, row):
        """
        transform raw csv row coming from the transactions file
        create namedtuple object with the transformed values
        """
        oldobj = klass._TransactionRecord(*row)
        newrow = klass.transform_namedtuple(oldobj)
        newobj = klass._TransactionRecord(*newrow)
        klass.validate(newobj)
        return newobj

    @classmethod
    def transform_namedtuple(klass, obj):
        """
        transform string values to required types - date, decimal numbers
        Decimals can be integers or with required precision
        """
        newrow = list(obj)
        obj_index = obj._fields.index
        for field in klass.MOD_DATE_LIST:
            index = obj_index(field)
            newrow[index] = date_parse(obj[index]).date()
        for field in klass.MOD_INT_LIST:
            index = obj_index(field)
            newrow[index] = klass.precision_int(Decimal(obj[index]))
        for field in klass.MOD_PR3_LIST:
            index = obj_index(field)
            newrow[index] = klass.precision_3(Decimal(obj[index]))
        return newrow

    @classmethod
    def scale_down(klass, transaction, rem_shares):
        t_index = transaction._fields.index
        value_index, recv_index, shares_index = map(t_index, (klass.VALUE_F, klass.RECEIVABLE_F, klass.SHARES_F))
        charges_index_list = map(t_index, (klass.BROKERAGE_F, klass.STT_F, klass.CHARGES_F))
        diff_ratio = rem_shares/transaction.shares
        newt = list(transaction)
        newt[shares_index] = rem_shares
        for index in [value_index] + charges_index_list:
            newt[index] = klass.precision_3(diff_ratio * newt[index])
        charges = sum([newt[index] for index in charges_index_list])
        newt[recv_index] = klass.precision_3(newt[value_index] - charges)
        newobj = klass._TransactionRecord(*newt)
        klass.validate(newobj)
        return newobj

    @classmethod
    def validate(klass, transaction):
        assert transaction.symbol and transaction.name
        assert transaction.trade in klass.TRADE_TYPES
        assert transaction.mode in klass.MODES
        if transaction.trade in (klass.DIV, klass.CSO, klass.CSI):
            return
        assert transaction.shares >= 0
        assert transaction.price > 0
        assert transaction.brokerage >= 0
        assert transaction.stt >= 0
        assert transaction.charges >= 0

