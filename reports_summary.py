#!/usr/bin/env python
import datetime, time
import json, requests
import texttable
from decimal import Decimal

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


class RealizedSummary(object):

    def __init__(self, stock_obj):
        self.stock_obj = stock_obj
        self.row_header = [
            'b_date', 's_date', 'b_price', 's_price', 'jan31', 'u_gain',
            'shares', 'b_value', 's_value', 'realized', 'b_charges',
            's_charges', 'n_charges', 'strg', 'ltrg', 'xtrg', 'percent'
        ]
        self.tbl_header = '%s (Realized Summary)' % self.stock_obj.name
        self.final_row = ['*--*'] * len(self.row_header)
        self.rows = []
        self.status = False


    def calculate_each_row(self, cg_obj):
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
            term = cg_obj.classify_term(buy_t.date, sel_t.date)
            xtrg = ltrg = strg = 0
            jan31_p = ''
            if term == 'long':
                ltrg = actual_gain
                if sel_t.date >= cg_obj.APR01_2018:
                    new_bp = buy_t.price
                    if buy_t.date <= cg_obj.JAN31_2018:
                        new_bp, jan31_p = cg_obj.grandfather_jan31_price(self.stock_obj.symbol, buy_t.price, sel_t.price)
                    tax_unit_gain = p3(sel_t.price - new_bp)
                    tax_realized = p3(sel_t.shares * tax_unit_gain)
                    if tax_realized != p3(Decimal('0')):    # don't make charges alone count to tax
                        xtrg = tax_realized - net_charges
            elif term == 'short':
                strg = actual_gain
            percent = '%s%%' % p3(actual_gain / buy_value * 100)
            data_row    = [
                buy_t.date, sel_t.date, buy_t.price, sel_t.price, jan31_p, unit_gain,
                sel_t.shares, buy_value, sel_value, realized, buy_charges,
                sel_charges, net_charges, strg, ltrg, xtrg, percent
            ]
            self.rows.append(data_row)

    def calculate_final_row(self):
        if len(self.rows) <= 0:
            return
        self.status = True
        p3 = self.stock_obj.precision_3
        p4 = self.stock_obj.precision_4
        self.final_row[0] = 'SUMMARY'
        for i in range(6, len(self.row_header)-1):
            self.final_row[i] = sum([row[i] for row in self.rows])
        shares = self.final_row[6]
        buy_value = self.final_row[7]
        sel_value = self.final_row[8]
        self.final_row[2] = p3(buy_value/shares)    # avg buy price of realized
        self.final_row[3] = p3(sel_value/shares)    # avg sell price of realized
        self.final_row[5] = p3(self.final_row[3] - self.final_row[2])
        actual_gains_sum = self.final_row[-4] + self.final_row[-3]
        self.final_row[-1] = '%s%%' % p3(actual_gains_sum / buy_value * 100)

    def print_summary(self):
        if len(self.rows) > 0:
            all_data = self.rows + [self.final_row]
            get_table(self.tbl_header, self.row_header, all_data)

    def main(self, cg_obj):
        self.calculate_each_row(cg_obj)
        self.calculate_final_row()


class HoldingSummary(object):

    def __init__(self, stock_obj):
        self.stock_obj = stock_obj
        self.row_header = [
            'b_date', 'shares', 'b_price', 'm_price', 'jan31', 'u_gain',
            'h_value', 'm_value', 'unrealized', 'b_charges',
            'stug', 'ltug', 'xtug', 'percent',
        ]
        self.tbl_header = '%s (Holding Summary)' % self.stock_obj.name
        self.final_row = ['*--*'] * len(self.row_header)
        self.rows = []
        self.status = False

    def calculate_each_row(self, cg_obj):
        assert self.stock_obj.sbuyq.is_empty() == True
        if self.stock_obj.dbuyq.is_empty() == True:
            return
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
            term = cg_obj.classify_term(buy_t.date, today_date)
            xtug = ltug = stug = 0
            jan31_p = ''
            if term == 'long':
                ltug = actual_gain
                if today_date >= cg_obj.APR01_2018:
                    new_bp = buy_t.price
                    if buy_t.date <= cg_obj.JAN31_2018:
                        new_bp, jan31_p = cg_obj.grandfather_jan31_price(self.stock_obj.symbol, buy_t.price, market_price)
                    tax_unit_gain = p3(market_price - new_bp)
                    tax_unrealized = p3(buy_t.shares * tax_unit_gain)
                    if tax_unrealized != p3(Decimal('0')):    # don't make charges alone count to tax
                        xtug = tax_unrealized - net_charges
            elif term == 'short':
                stug = actual_gain
            percent = '%s%%' % p3(actual_gain / hold_value * 100)
            data_row = [
                buy_t.date, buy_t.shares, buy_t.price, market_price, jan31_p, unit_gain,
                hold_value, market_value, unrealized, net_charges,
                stug, ltug, xtug, percent
            ]
            self.rows.append(data_row)

    def calculate_final_row(self):
        if len(self.rows) <= 0:
            return
        self.status = True
        p3 = self.stock_obj.precision_3
        self.final_row[0] = 'SUMMARY'
        self.final_row[1] = sum([row[1] for row in self.rows])
        for i in range(6, len(self.row_header)-1):
            self.final_row[i] = sum([row[i] for row in self.rows])
        self.final_row[2] = self.final_row[6]/self.final_row[1] # avg buy
        self.final_row[3] = self.final_row[7]/self.final_row[1] # avg mkt
        self.final_row[5] = self.final_row[3] - self.final_row[2]
        net_unrealized = self.final_row[-3] + self.final_row[-4]
        self.final_row[-1] = '%s%%' % p3((net_unrealized*100)/self.final_row[6])


    def try_api_call(self, url, params):
        retries = 0
        while retries < 6:
            retries += 1
            time.sleep(2)
            rsp = requests.get(url, params=params)
            if rsp.status_code != 200:
                print 'retry = %s, status = %s, params = %s' % (retries, rsp.status_code, params)
                continue
            fin_data = json.loads(rsp.content)
            if "Error Message" in fin_data:
                print 'retry = %s, status = %s, params = %s, data = %s' % (retries, rsp.status_code, params, fin_data)
                continue
            break
        return rsp, fin_data

    def get_market_price(self):
        if self.stock_obj.symbol == 'Capital':
            return Decimal(0)
        time.sleep(1)
        market, symbol = self.stock_obj.symbol.split(':')
        if market == 'BOM':
            market = 'BSE'
        url = "https://www.alphavantage.co/query"
        interval = '60min'
        params = { 'apikey': '417VIWXIWW71MYDT', 'function': 'TIME_SERIES_INTRADAY', 'market': market, 'symbol': symbol, 'interval': interval }
        #url = "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&apikey=417VIWXIWW71MYDT&market=%s&symbol=%s&interval=60min" % (market, symbol)
        #url = "https://finance.google.com/finance?q=%s&output=json" % self.stock_obj.symbol

        rsp, fin_data = self.try_api_call(url, params)
        try:
            last_refr = fin_data["Meta Data"]["3. Last Refreshed"]
            market_price_str = fin_data["Time Series (%s)" % interval][last_refr]["4. close"]
        except:
            print 'ERROR %s after RETRIES: %s' % (rsp.status_code, rsp.content)
            import pdb; pdb.set_trace()
        return self.stock_obj.precision_3(Decimal(market_price_str))


    def print_summary(self):
        if len(self.rows) > 0:
            all_data = self.rows + [self.final_row]
            get_table(self.tbl_header, self.row_header, all_data)

    def main(self, cg_obj):
        self.calculate_each_row(cg_obj)
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
            'n_charges', 'n_realized', 'percent', 'strg', 'ltrg', 'xtrg'
        ]
        self.h_tbl_header = '%s (One Line Holding Summary)' % self.name
        self.h_row_header = [
            'h_value', 'm_value', 'shares', 'a_price', 'm_price', 'h_charges',
            'a_cost', 'u_gain', 'n_unrealized', 'percent', 'stug', 'ltug', 'xtug'
        ]
        self.final_r_row = []
        self.final_h_row = []

    def calculate_final_row(self, cg_obj):
        self.realized_summary.main(cg_obj)
        self.holding_summary.main(cg_obj)
        h_row = self.holding_summary.final_row
        r_row = self.realized_summary.final_row

        if self.realized_summary.status:
            n_realized = r_row[-3] + r_row[-4]
            self.final_r_row = r_row[7:13]
            self.final_r_row += [n_realized, r_row[-1], r_row[-4], r_row[-3], r_row[-2]]

        if self.holding_summary.status:
            data_2_row = [h_row[6], h_row[7]] + h_row[1:4] + [h_row[9]]
            a_cost = (h_row[6] + h_row[9]) / h_row[1]
            u_gain = h_row[3] - a_cost
            n_unrealized = h_row[-3] + h_row[-4]
            data_2_row.extend([a_cost, u_gain, n_unrealized, h_row[-1]])
            data_2_row.extend([h_row[-4], h_row[-3], h_row[-2]])
            self.final_h_row = data_2_row

    def main(self, cg_obj):
        self.calculate_final_row(cg_obj)

    def print_summary(self):
        if self.final_r_row:
            get_table(self.r_tbl_header, self.r_row_header, [self.final_r_row])
            self.realized_summary.print_summary()
        if self.final_h_row:
            get_table(self.h_tbl_header, self.h_row_header, [self.final_h_row])
            self.holding_summary.print_summary()


class PortFolioSummary(object):
    def __init__(self, pf_obj, cg_obj):
        self.pf_obj = pf_obj
        self.r_tbl_header = "PortFolio Realized Summmary"
        self.r_rows = []
        self.h_tbl_header = "PortFolio Holding Summmary"
        self.h_rows = []
        self.cg_obj = cg_obj

    def print_summary(self):
        for symbol, stock_obj in self.pf_obj.stock_hash.iteritems():
            ss = stock_obj.stock_summary
            p3 = stock_obj.precision_3
            r_row_header = ['name'] + ss.r_row_header
            h_row_header = ['name'] + ss.h_row_header
            ss.main(self.cg_obj)
            ss.print_summary()
            name = stock_obj.name.split()[0]
            if ss.final_r_row:
                self.r_rows.append([name] + ss.final_r_row)
            if ss.final_h_row:
                self.h_rows.append([name] + ss.final_h_row)
        if self.r_rows:
            final_row = ['*--*'] * len(r_row_header)
            for i in range(1, 8) + [9, 10, 11]:
                final_row[i] = sum([row[i] for row in self.r_rows])
            final_row[0] = 'SUMMARY'
            final_row[-4] = '%s%%' % p3(final_row[-5]*100/final_row[1])
            self.r_rows.append(final_row)
            get_table(self.r_tbl_header, r_row_header, self.r_rows)
        if self.h_rows:
            final_row = ['*--*'] * len(h_row_header)
            final_row[0] = 'SUMMARY'
            for i in (1,2,6,9,11,12,13):
                final_row[i] = sum([row[i] for row in self.h_rows])
            final_row[-4] = '%s%%' % p3(final_row[-5]*100/final_row[1])
            self.h_rows.append(final_row)
            get_table(self.h_tbl_header, h_row_header, self.h_rows)

