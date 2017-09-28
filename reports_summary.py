#!/usr/bin/env python
import texttable
import datetime, time
from decimal import Decimal
from googlefinance import getQuotes
import json, requests

def get_table(table_header, header_row, data):
    if not data:
        return
    data = [header_row] + data
    table = texttable.Texttable(195)
    table.header(header_row)
    table.add_rows(data)
    align_row = ['l', 'l'] + ['r'] * (len(header_row) - 2)
    table.set_cols_align(align_row)
    tbl_hdr_len = len(table_header) + 1
    print "\n%s\n%s\n" % (table_header, '='*tbl_hdr_len)
    print table.draw()

def classify_gain(buy_date, reference_date, gain):
    short_term, long_term = 0, 0
    assert reference_date >= buy_date
    date_diff = reference_date - buy_date
    if date_diff.days > 365:
        long_term = gain
    else:
        short_term = gain
    return short_term, long_term

class RealizedSummary(object):

    def __init__(self, stock_obj):
        self.stock_obj = stock_obj
        self.row_header = [
            'b_date', 's_date', 'b_price', 's_price', 'u_gain',
            'shares', 'b_value', 's_value', 'realized', 'b_charges',
            's_charges', 'n_charges', 'strg', 'ltrg', 'percent'
        ]
        self.tbl_header = '%s (Realized Summary)' % self.stock_obj.name
        self.final_row = ['*--*'] * len(self.row_header)
        self.rows = []
        self.status = False

    def calculate_each_row(self):
        p3 = self.stock_obj.precision_3
        p4 = self.stock_obj.precision_4
        for (sel_t, buy_t) in self.stock_obj.realized_list:
            assert sel_t.shares == buy_t.shares
            unit_gain   = p4(sel_t.price - buy_t.price)
            buy_value = p3(buy_t.shares * buy_t.price)
            sel_value = p3(sel_t.shares * sel_t.price)
            realized    = p3(sel_t.shares * unit_gain)
            buy_charges = p3(buy_t.brokerage + buy_t.stt + buy_t.charges)
            sel_charges = p3(sel_t.brokerage + sel_t.stt + sel_t.charges)
            net_charges = p3(sel_charges + buy_charges)
            actual_gain = realized - net_charges
            strg, ltrg  = classify_gain(buy_t.date, sel_t.date, actual_gain)
            percent = '%s%%' % p3(actual_gain / buy_value * 100)
            data_row    = [
                buy_t.date, sel_t.date, buy_t.price, sel_t.price, unit_gain,
                sel_t.shares, buy_value, sel_value, realized, buy_charges,
                sel_charges, net_charges, strg, ltrg, percent
            ]
            self.rows.append(data_row)

    def calculate_final_row(self):
        if len(self.rows) <= 0:
            return
        self.status = True
        p3 = self.stock_obj.precision_3
        p4 = self.stock_obj.precision_4
        self.final_row[0] = 'SUMMARY'
        for i in range(5, len(self.row_header)-1):
            self.final_row[i] = sum([row[i] for row in self.rows])
        shares = self.final_row[5]
        buy_value = self.final_row[6]
        sel_value = self.final_row[7]
        self.final_row[2] = p3(buy_value/shares)    # avg buy price of realized
        self.final_row[3] = p3(sel_value/shares)    # avg sell price of realized
        self.final_row[4] = p3(self.final_row[3] - self.final_row[2])
        actual_gains_sum = self.final_row[-3] + self.final_row[-2]
        self.final_row[-1] = '%s%%' % p3(actual_gains_sum / buy_value * 100)

    def print_summary(self):
        if len(self.rows) > 0:
            all_data = self.rows + [self.final_row]
            get_table(self.tbl_header, self.row_header, all_data)

    def main(self):
        self.calculate_each_row()
        self.calculate_final_row()


class HoldingSummary(object):

    def __init__(self, stock_obj):
        self.stock_obj = stock_obj
        self.row_header = [
            'b_date', 'shares', 'b_price', 'm_price', 'u_gain',
            'h_value', 'm_value', 'unrealized', 'b_charges',
            'stug', 'ltug', 'percent',
        ]
        self.tbl_header = '%s (Holding Summary)' % self.stock_obj.name
        self.final_row = ['*--*'] * len(self.row_header)
        self.rows = []
        self.status = False

    def calculate_each_row(self):
        assert self.stock_obj.sbuyq.is_empty() == True
        market_price = self.get_market_price()
        today_date = datetime.datetime.now().date()
        p3 = self.stock_obj.precision_3
        for buy_t in self.stock_obj.dbuyq:
            unit_gain = market_price - buy_t.price
            hold_value = buy_t.shares * buy_t.price
            market_value = buy_t.shares * market_price
            unrealized = market_value - hold_value
            buy_charges = sum([buy_t.brokerage, buy_t.stt, buy_t.charges])
            net_charges = self.stock_obj.precision_3(buy_charges)
            actual_gain = unrealized - net_charges
            stug, ltug = classify_gain(buy_t.date, today_date, actual_gain)
            percent = '%s%%' % p3(actual_gain / hold_value * 100)
            data_row = [
                buy_t.date, buy_t.shares, buy_t.price, market_price, unit_gain,
                hold_value, market_value, unrealized, net_charges,
                stug, ltug, percent
            ]
            self.rows.append(data_row)

    def calculate_final_row(self):
        if len(self.rows) <= 0:
            return
        self.status = True
        p3 = self.stock_obj.precision_3
        self.final_row[0] = 'SUMMARY'
        self.final_row[1] = sum([row[1] for row in self.rows])
        for i in range(5, len(self.row_header)-1):
            self.final_row[i] = sum([row[i] for row in self.rows])
        self.final_row[2] = self.final_row[5]/self.final_row[1] # avg buy
        self.final_row[3] = self.final_row[6]/self.final_row[1] # avg mkt
        self.final_row[4] = self.final_row[3] - self.final_row[2]
        net_unrealized = self.final_row[-2] + self.final_row[-3]
        self.final_row[-1] = '%s%%' % p3((net_unrealized*100)/self.final_row[5])

    def get_market_price(self):
        #time.sleep(2)
        if self.stock_obj.symbol == 'Capital':
            return Decimal(0)
        url = "https://finance.google.com/finance?q=%s&output=json" % self.stock_obj.symbol
        rsp = requests.get(url)
        assert rsp.status_code == 200
        fin_data = json.loads(rsp.content[6:-2].decode('unicode_escape'))
        assert fin_data["e"] in ('NSE', 'BOM')
        market_price_str = fin_data["l"].replace(',', '')
        return self.stock_obj.precision_3(Decimal(market_price_str))

        quote_list = getQuotes(self.stock_obj.symbol)
        #print self.symbol
        assert len(quote_list) == 1
        quote_dict = quote_list[0]
        assert quote_dict['Index'] in ('NSE', 'BOM')
        market_price_str = quote_dict[u'LastTradePrice'].replace(',','')
        return self.stock_obj.precision_3(Decimal(market_price_str))

    def print_summary(self):
        if len(self.rows) > 0:
            all_data = self.rows + [self.final_row]
            get_table(self.tbl_header, self.row_header, all_data)

    def main(self):
        self.calculate_each_row()
        self.calculate_final_row()


class DividendSummary(object):

    def __init__(self, stock_obj):
        self.stock_obj = stock_obj

class StockSummary(object):

    def __init__(self, stock_obj):
        self.realized_summary   = RealizedSummary(stock_obj)
        self.holding_summary    = HoldingSummary(stock_obj)
        self.stock_obj          = stock_obj
        self.name               = self.stock_obj.name
        self.r_tbl_header = '%s (One Line Realized Summary)' % self.name
        self.r_row_header = [
            'b_value', 's_value', 'realized', 'b_charges', 's_charges',
            'n_charges', 'n_realized', 'percent', 'strg', 'ltrg'
        ]
        self.h_tbl_header = '%s (One Line Holding Summary)' % self.name
        self.h_row_header = [
            'h_value', 'm_value', 'shares', 'a_price', 'm_price', 'h_charges',
            'a_cost', 'u_gain', 'n_unrealized', 'percent', 'stug', 'ltug',
        ]
        self.final_r_row = []
        self.final_h_row = []

    def calculate_final_row(self):
        self.realized_summary.main()
        self.holding_summary.main()
        h_row = self.holding_summary.final_row
        r_row = self.realized_summary.final_row

        if self.realized_summary.status:
            n_realized = r_row[-2] + r_row[-3]
            self.final_r_row = r_row[6:12]
            self.final_r_row += [n_realized, r_row[-1], r_row[-3], r_row[-2]]

        if self.holding_summary.status:
            data_2_row = [h_row[5], h_row[6]] + h_row[1:4] + [h_row[8]]
            a_cost = (h_row[5] + h_row[8]) / h_row[1]
            u_gain = h_row[3] - a_cost
            n_unrealized = h_row[-2] + h_row[-3]
            data_2_row.extend([a_cost, u_gain, n_unrealized, h_row[-1]])
            data_2_row.extend([h_row[-3], h_row[-2]])
            self.final_h_row = data_2_row

    def main(self):
        self.calculate_final_row()

    def print_summary(self):
        if self.final_r_row:
            get_table(self.r_tbl_header, self.r_row_header, [self.final_r_row])
            self.realized_summary.print_summary()
        if self.final_h_row:
            get_table(self.h_tbl_header, self.h_row_header, [self.final_h_row])
            self.holding_summary.print_summary()


class PortFolioSummary(object):
    def __init__(self, pf_obj):
        self.pf_obj = pf_obj
        self.r_tbl_header = "PortFolio Realized Summmary"
        self.r_rows = []
        self.h_tbl_header = "PortFolio Holding Summmary"
        self.h_rows = []

    def print_summary(self):
        for symbol, stock_obj in self.pf_obj.stock_hash.iteritems():
            ss = stock_obj.stock_summary
            p3 = stock_obj.precision_3
            r_row_header = ['name'] + ss.r_row_header
            h_row_header = ['name'] + ss.h_row_header
            ss.main()
            ss.print_summary()
            name = stock_obj.name.split()[0]
            if ss.final_r_row:
                self.r_rows.append([name] + ss.final_r_row)
            if ss.final_h_row:
                self.h_rows.append([name] + ss.final_h_row)
        if self.r_rows:
            final_row = ['*--*'] * len(r_row_header)
            for i in range(1, 8) + [9, 10]:
                final_row[i] = sum([row[i] for row in self.r_rows])
            final_row[0] = 'SUMMARY'
            final_row[-3] = '%s%%' % p3(final_row[-4]*100/final_row[1])
            self.r_rows.append(final_row)
            get_table(self.r_tbl_header, r_row_header, self.r_rows)
        if self.h_rows:
            final_row = ['*--*'] * len(h_row_header)
            final_row[0] = 'SUMMARY'
            for i in (1,2,6,9,11,12):
                final_row[i] = sum([row[i] for row in self.h_rows])
            final_row[10] = '%s%%' % p3(final_row[9]*100/final_row[1])
            self.h_rows.append(final_row)
            get_table(self.h_tbl_header, h_row_header, self.h_rows)

