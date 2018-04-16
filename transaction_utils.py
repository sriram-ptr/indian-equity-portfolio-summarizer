#!/usr/bin/env python

"""
* Transaction based utilities are implemented in this module
* Author: Sriram Ponnusamy
* Feel free to use and distribute for any good purpose with good intentions
"""

import datetime
from collections import namedtuple
from dateutil.parser import parse as date_parse
from decimal import Decimal
from stock_exchange_tools import Precision


class TransactionQueue(object):
    """
    queue implementation to hold transactions in a portfolio
    """
    _ZERO = 0

    def __init__(self):
        self.items = []

    def is_empty(self):
        return len(self.items) == self._ZERO

    def size(self):
        return len(self.items)

    def put(self, item, front):
        if front == True:
            self.items.insert(self._ZERO, item)
        else:
            self.items.append(item)

    def get(self):
        return self.items.pop(self._ZERO)

    def __iter__(self):
        return self.items.__iter__()


class TransactionConstants(object):
    """
    class defines all constants involved in a transaction
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

    # gain type for taxation
    LONG_TERM       = 'long'
    SHORT_TERM      = 'short'
    TERM_DAYS_DIFF  = 365

    # indian exchanges
    BSE_EXCH = 'BSE'
    NSE_EXCH = 'NSE'

    # buy and sale date from when LTCG becomes taxable
    APR01_2018 = datetime.datetime(2018, 4, 1).date()
    JAN31_2018 = datetime.datetime(2018, 1, 31).date()

    CSV_FILE_MODE   = 'rUb'

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
    RECEIVABLE_F    = 'receivable'
    MODE_F          = 'mode'

    # order of transaction fields
    TRANSACTION_FIELDS = [
        SYMBOL_F, NAME_F, TRADE_F, DATE_F, SHARES_F, PRICE_F, VALUE_F,
        BROKERAGE_F, STT_F, CHARGES_F, RECEIVABLE_F, MODE_F
    ]

    # fields to be accessed based on types or logical groups
    AMOUNT_F_LIST   = [PRICE_F, VALUE_F, RECEIVABLE_F]
    CHARGES_F_LIST  = [BROKERAGE_F, STT_F, CHARGES_F]
    DATE_F_LIST     = [DATE_F]
    INTEGER_F_LIST  = [SHARES_F]
    PRECI3_F_LIST   = AMOUNT_F_LIST + CHARGES_F_LIST #[PRICE_F, VALUE_F, BROKERAGE_F, STT_F, CHARGES_F, RECEIVABLE_F]


TransactionMeta = namedtuple('TransactionMeta', TransactionConstants.TRANSACTION_FIELDS)

class TransactionRecord(TransactionMeta, TransactionConstants):
    """
    namedtuple TransactionMeta class to access each field in a row as an object attribute
    the object is immutable but we have use cases like the following. They are implmented as methods.
        1.  transform values of certain fields after reading from the file
        2.  scale down a partially realized buy transaction based on number of shares realized
        3.  creating an equivalent sell transaction for an unrealized buy transaction based on today's date
            and current market price. This makes handling realized and holding transactions uniform.
    """

    _record_field_index = {field: index for (index, field) in enumerate(TransactionMeta._fields)}

    def __new__(cls, row, transform=True):
        """
        overriding __new__ as TransactionMeta derives from tuple class
        immutable object so call new again after transforming values of certain fields
        do a validation before returning the object
        """
        obj = super(TransactionRecord, cls).__new__(cls, *row)
        if transform:
            newrow = obj.transform_namedtuple()
            obj = super(TransactionRecord, cls).__new__(cls, *newrow)
        obj.validate()
        return obj

    @classmethod
    def create_obj_from_row(cls, row, transform=True):
        """
        one more method apart from __new__ to create object as there are instance methods
        with a need to create objects. Those instance methods can call this method. Note that
        this method actually makes a call to __new__
        """
        obj = cls(row, transform)
        return obj

    def __repr__(self):
        val = super(self.__class__, self).__repr__()
        return val.replace(super(self.__class__, self).__class__.__name__, self.__class__.__name__)

    def transform_namedtuple(self):
        """
        transform string values to required types - date, decimal numbers with required precision
        the basic object exists in __new__ to call this and hence this is made an instance method
        this method is called from __new__, technically considered as part of object creation
        hence, do not call create_obj_from_row from here as that would be calling __new__ again
        """
        newrow = list(self)
        rf_index = self._record_field_index
        for index in (rf_index[field] for field in self.DATE_F_LIST):
            newrow[index] = date_parse(self[index]).date()
        for index in (rf_index[field] for field in self.INTEGER_F_LIST):
            newrow[index] = Precision.integer(Decimal(self[index]))
        for index in (rf_index[field] for field in self.PRECI3_F_LIST):
            newrow[index] = Precision.three(Decimal(self[index]))
        return newrow

    def scale_down(self, rem_shares):
        """
        scale down a partially realized buy transaction(self) based on number of shares remaining after
        realization. shares, value and charges scaled down using the ratio rem_shares/original_shares.
        receivable can also be scaled down but recalculation preferred for precision
        """
        rf_index = self._record_field_index
        value_index, recv_index, shares_index = [rf_index[x] for x in (self.VALUE_F, self.RECEIVABLE_F, self.SHARES_F)]
        charges_index_list = [rf_index[x] for x in self.CHARGES_F_LIST]
        diff_ratio = rem_shares/self.shares
        newt = list(self)
        newt[shares_index] = rem_shares
        for index in [value_index] + charges_index_list:
            newt[index] = Precision.three(diff_ratio * newt[index])
        charges = sum([newt[index] for index in charges_index_list])
        newt[recv_index] = Precision.three(newt[value_index] - charges) # receivable can also be scaled down, this is preferred for precision
        return self.create_obj_from_row(newt, transform=False)

    def get_ref_sel_transaction(self, ref_date, market_price):
        """
        create an equivalent sell transaction for an unrealized buy transaction based on
        today's date and current market price. Trade changed to sell, Price unchanged,
        Charges made zero, Value and Receivable recalculated again. This method makes
        calculation of holding gains same as the method to calculate realized gains
        """
        rf_index = self._record_field_index
        newt = list(self)
        newt[rf_index[self.TRADE_F]] = self.SEL
        newt[rf_index[self.DATE_F]] = ref_date
        newt[rf_index[self.PRICE_F]] = market_price
        value_index = rf_index[self.VALUE_F]
        newt[value_index] = Precision.three(self.shares * market_price)
        for index in (rf_index[x] for x in self.CHARGES_F_LIST):
            newt[index] = Precision.DECIMAL_ZERO
        newt[rf_index[self.RECEIVABLE_F]] = Precision.three(newt[value_index]) # charges are zero
        return self.create_obj_from_row(newt, transform=False)

    def validate(self):
        """
        just do a sanity check on various fields
        the basic object exists in __new__ to call this and hence this is made an instance method
        """
        assert self.symbol and self.name
        assert self.trade in self.TRADE_TYPES
        assert self.mode in self.MODES
        if self.trade in (self.DIV, self.CSO, self.CSI):
            return
        assert self.shares >= 0
        assert self.price > 0
        assert self.brokerage >= 0
        assert self.stt >= 0
        assert self.charges >= 0

