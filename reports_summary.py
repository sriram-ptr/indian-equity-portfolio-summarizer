#!/usr/bin/env python
import datetime, time
import json, requests
import texttable
from transaction_utils import Precision, Decimal

def get_table(table_header, header_row, data):
    if not data:
        return
    data = [header_row] + data
    table = texttable.Texttable(230)
    table.header(header_row)
    table.add_rows(data)
    align_row = ['l', 'l'] + ['r'] * (len(header_row) - 2)
    table.set_cols_align(align_row)
    tbl_hdr_len = len(table_header) + 1
    print "\n%s\n%s\n" % (table_header, '='*tbl_hdr_len)
    print table.draw()



class DetailsTableRow(object):

    def __init__(self, cg_obj):
        self.cg_obj = cg_obj

    @property
    def name(self):
        return self.cg_obj.buy_t.name

    @property
    def b_date(self):
        return self.cg_obj.buy_t.date

    @property
    def s_date(self):
        return self.cg_obj.sel_t.date

    @property
    def b_value(self):
        return self.cg_obj.buy_value

    @property
    def h_value(self):
        return self.b_value

    @property
    def s_value(self):
        return self.cg_obj.sel_value

    @property
    def m_value(self):
        return self.s_value

    @property
    def g_gain(self):
        return self.cg_obj.gross_gain

    @property
    def j_price(self):
        return self.cg_obj.jan31_price

    @property
    def b_price(self):
        return self.cg_obj.buy_t.price

    @property
    def h_price(self):
        return self.b_price

    @property
    def x_price(self):
        return self.cg_obj.tax_buy_price

    @property
    def s_price(self):
        return self.cg_obj.sel_t.price

    @property
    def m_price(self):
        return self.s_price

    @property
    def u_pgain(self):
        return self.cg_obj.unit_pgain

    @property
    def u_cgain(self):
        return Precision.three((self.s_value - self.b_value - self.b_charges)/self.shares)

    @property
    def b_charges(self):
        return self.cg_obj.buy_charges

    @property
    def h_charges(self):
        return self.b_charges

    @property
    def b_cost(self):
        return Precision.three((self.cg_obj.buy_value + self.cg_obj.buy_charges)/self.shares)

    @property
    def h_cost(self):
        return self.b_cost

    @property
    def shares(self):
        return self.cg_obj.sel_t.shares

    @property
    def s_charges(self):
        return self.cg_obj.sel_charges

    @property
    def n_charges(self):
        return self.cg_obj.net_charges

    @property
    def n_gain(self):
        return self.s_value - self.b_value - self.n_charges

    @property
    def stg(self):
        return self.cg_obj.short_gain

    @property
    def ltg(self):
        return self.cg_obj.long_gain

    @property
    def xltg(self):
        return self.cg_obj.tax_long_gain

    @property
    def percent(self):
        return self.cg_obj.gain_perc

class SummaryTableRow(object):

    def __init__(self, cg_obj_list):
        self.cg_obj_list = cg_obj_list
        self.cosmetic_value = '*--*'

    @property
    def name(self):
        return self.cosmetic_value

    @property
    def b_date(self):
        return  self.cosmetic_value

    @property
    def s_date(self):
        return self.cosmetic_value

    @property
    def b_value(self):
        return sum([cg_obj.buy_value for cg_obj in self.cg_obj_list])

    @property
    def h_value(self):
        return self.b_value

    @property
    def s_value(self):
        return sum([cg_obj.sel_value for cg_obj in self.cg_obj_list])

    @property
    def m_value(self):
        return self.s_value

    @property
    def g_gain(self):
        return sum([cg_obj.gross_gain for cg_obj in self.cg_obj_list])

    @property
    def shares(self):
        return sum([cg_obj.sel_t.shares for cg_obj in self.cg_obj_list])

    @property
    def j_price(self):
        if len(self.cg_obj_list) > 0:
            return self.cg_obj_list[0].jan31_price
        return Precision.DECIMAL_ZERO

    @property
    def b_price(self):
        if self.shares <= 0:
            import pdb; pdb.set_trace()
        return Precision.three(self.b_value/self.shares)

    @property
    def h_price(self):
        return self.b_price

    @property
    def x_price(self):
        tax_buy_value = sum([cg_obj.tax_buy_value for cg_obj in self.cg_obj_list])
        return Precision.three(tax_buy_value/self.shares)

    @property
    def s_price(self):
        return Precision.three(self.s_value/self.shares)

    @property
    def m_price(self):
        return self.s_price

    @property
    def b_charges(self):
        return sum([cg_obj.buy_charges for cg_obj in self.cg_obj_list])

    @property
    def h_charges(self):
        return self.b_charges

    @property
    def b_cost(self):
        return Precision.three((self.b_value + self.b_charges)/self.shares)

    @property
    def h_cost(self):
        return self.b_cost

    @property
    def u_pgain(self):
        return Precision.three((self.s_value - self.b_value)/self.shares)

    @property
    def u_cgain(self):
        return Precision.three((self.s_value - self.b_value - self.b_charges)/self.shares)

    @property
    def s_charges(self):
        return sum([cg_obj.sel_charges for cg_obj in self.cg_obj_list])

    @property
    def n_charges(self):
        return sum([cg_obj.net_charges for cg_obj in self.cg_obj_list])

    @property
    def n_gain(self):
        return self.s_value - self.b_value - self.n_charges

    @property
    def stg(self):
        return sum([cg_obj.short_gain for cg_obj in self.cg_obj_list])

    @property
    def ltg(self):
        return sum([cg_obj.long_gain for cg_obj in self.cg_obj_list])

    @property
    def xltg(self):
        return sum([cg_obj.tax_long_gain for cg_obj in self.cg_obj_list])

    @property
    def percent(self):
        return Precision.percent(self.n_gain, self.b_value)


class StockSummary(object):

    def __init__(self, stock_obj):
        self.stock_obj = stock_obj
        self.name = self.stock_obj.name
        # realized stuff
        self.realized_status = False
        self.realized_details_table = []
        self.realized_details_title = '%s (Realized Details)' % self.name
        self.realized_details_header = [
            'b_date', 's_date', 'shares', 'b_value', 's_value', 'b_price', 's_price', 'u_pgain', 'g_gain', 'b_charges', 'b_cost',
            'u_cgain', 's_charges', 'n_charges', 'n_gain', 'percent', 'j_price', 'x_price', 'stg', 'ltg', 'xltg'
        ]
        self.realized_summary_table = []
        self.realized_summary_title = '%s (One Line Realized Summary)' % self.name
        self.realized_summary_header = [
            'shares', 'b_value', 's_value', 'b_price', 's_price', 'u_pgain', 'g_gain', 'b_charges', 'b_cost', 'u_cgain',
            's_charges', 'n_charges', 'n_gain', 'percent', 'j_price', 'stg', 'ltg', 'xltg'
        ]
        # holding stuff
        self.holding_status = False
        self.holding_details_table = []
        self.holding_details_title = '%s (Holding Details)' % self.name
        self.holding_details_header = [
            'b_date', 'shares', 'b_value', 's_value', 'b_price', 's_price', 'u_pgain', 'g_gain', 'b_charges', 'b_cost',
            'u_cgain', 's_charges', 'n_charges', 'n_gain', 'percent', 'j_price', 'x_price', 'stg', 'ltg', 'xltg'
        ]
        self.holding_summary_table = []
        self.holding_summary_title = '%s (One Line Holding Summary)' % self.name
        self.holding_summary_header = [
            'shares', 'b_value', 's_value', 'b_price', 's_price', 'u_pgain', 'g_gain', 'b_charges', 'b_cost',
            'u_cgain', 's_charges', 'n_charges', 'n_gain', 'percent', 'j_price', 'stg', 'ltg', 'xltg'
        ]

    def create_details_table(self, cg_obj_list, table_tuple):
        t_table, t_header = table_tuple
        flag = False
        for cg_obj in cg_obj_list:
            cg_obj.calculate()
            dt_obj = DetailsTableRow(cg_obj)
            data_row = [getattr(dt_obj, field) for field in t_header]
            t_table.append(data_row)
            flag = True
        return flag

    def create_summary_table(self, cg_obj_list, table_tuple):
        t_table, t_header = table_tuple
        st_obj = SummaryTableRow(cg_obj_list)
        data_row = [getattr(st_obj, field) for field in t_header]
        t_table.append(data_row)
        return st_obj

    def add_final_row(self, st_obj, table_tuple, table_status):
        if table_status == False:
            return
        t_table, t_header = table_tuple
        data_row = [getattr(st_obj, field) for field in t_header]
        t_table.append(data_row)

    def realized_output(self):
        rdt_tuple = (self.realized_details_table, self.realized_details_header)
        self.realized_status = self.create_details_table(self.stock_obj.realized_list, rdt_tuple)
        if self.realized_status == False:
            return
        rst_tuple = (self.realized_summary_table, self.realized_summary_header)
        st_obj = self.create_summary_table(self.stock_obj.realized_list, rst_tuple)
        self.add_final_row(st_obj, rdt_tuple, self.realized_status)

    def holding_output(self):
        hdt_tuple = (self.holding_details_table, self.holding_details_header)
        self.holding_status = self.create_details_table(self.stock_obj.holding_list, hdt_tuple)
        if self.holding_status == False:
            return
        hst_tuple = (self.holding_summary_table, self.holding_summary_header)
        st_obj = self.create_summary_table(self.stock_obj.holding_list, hst_tuple)
        self.add_final_row(st_obj, hdt_tuple, self.holding_status)

    def print_summary(self):
        self.realized_output()
        self.holding_output()
        if self.realized_status:
            get_table(self.realized_details_title, self.realized_details_header, self.realized_details_table)
            get_table(self.realized_summary_title, self.realized_summary_header, self.realized_summary_table)
        if self.holding_status:
            get_table(self.holding_details_title, self.holding_details_header, self.holding_details_table)
            get_table(self.holding_summary_title, self.holding_summary_header, self.holding_summary_table)


class PortFolioSummary(object):
    def __init__(self, pf_obj):
        self.pf_obj = pf_obj
        self.sum_fields = ('b_value', 's_value', 'b_charges', 's_charges', 'n_charges', 'g_gain', 'n_gain', 'stg', 'ltg', 'xltg')
        self.percent_fields = ('percent', )
        self.cosmetic_value = '*--*'
        self.name_field = 'name'

        self.r_details_table = []
        self.r_details_title = "PortFolio Realized Summmary"
        self.r_details_header = []
        self.r_details_finalrow = []
        self.r_status = False

        self.h_details_table = []
        self.h_details_title = "PortFolio Holding Summmary"
        self.h_details_header = []
        self.h_details_finalrow = []
        self.h_status = False

    def add_final_row(self, header, table):
        data_row = [self.cosmetic_value] * len(header)
        for sum_field in self.sum_fields:
            sum_index = header.index(sum_field)
            assert sum_index >= 0
            data_row[sum_index] = sum([row[sum_index] for row in table])
        percent_index = header.index('percent')
        if percent_index != -1:
            buy_value_index = header.index('b_value')
            net_gain_index = header.index('n_gain')
            data_row[percent_index] = Precision.percent(data_row[net_gain_index], data_row[buy_value_index])
        table.append(data_row)

    def print_summary(self):
        for symbol, stock_obj in self.pf_obj.stock_hash.iteritems():
            ss = stock_obj.stock_summary
            ss.print_summary()
            name = stock_obj.name.split()[0]
            if ss.realized_status:
                self.r_details_header = [self.name_field] + ss.realized_summary_header
                self.r_details_table.append([name] + ss.realized_summary_table[-1])
                self.r_status = True
            if ss.holding_status:
                self.h_details_header = [self.name_field] + ss.holding_summary_header
                self.h_details_table.append([name] + ss.holding_summary_table[-1])
                self.h_status = True
        if self.r_status:
            self.add_final_row(self.r_details_header, self.r_details_table)
            get_table(self.r_details_title, self.r_details_header, self.r_details_table)
        if self.h_status:
            self.add_final_row(self.h_details_header, self.h_details_table)
            get_table(self.h_details_title, self.h_details_header, self.h_details_table)
