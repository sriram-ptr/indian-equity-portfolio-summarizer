# Indian Equity Portfolio Summarizer
* Given the equity portfolio transactions as a CSV file(refer `sample_portfolio.csv` in the repository), you can get the following information:
  * For each stock:
    * one line realized summary with the short term realized gain/loss, long term realized gain/loss and total realized gain/loss
    * details on each sell transaction where a gain or loss was realized, matched against its buy transaction
    * one line holding summary with the short term unrealized gain/loss, long term unrealized gain/loss and total unrealized gain/loss
    * details on each buy transaction where there is no corresponding sell transaction (shares being held)
  * For whole portfolio:
    * Realized Summary - one line per stock giving the short term and long term gain/loss realized from the stock
    * Holding Summary - one line per stock which are being held with the short and long term unrealized gain/loss from the stock
* Only transactions on Indian Stock exchanges NSE and BSE are supported.
* It also classifies the gain/loss as Short Term or Long Term capital gains according to Indian income tax laws. At the time of this writing, any gain/loss realized by selling a stock after one year since buying will be Long term capital gain and the same realized within one year would be Short term capital gain. 
* Indian Budget 2018 made long term capital gains taxable at 10% without indexation for shares sold on or after Apr 01, 2018. For the shares sold on or after Apr 01, 2018, the buy price is grandfathered based on the stock price on Jan 31, 2018 provided it is a long term transaction and the shares were bought before Jan 31, 2018.

## Requirements to run this code ##
* Transactions in a CSV file in the format explained below (you can refer `sample_portfolio.csv` in the repository)
* Python 2.7 or any version higher than that
* _googlefinance_ library, google finance APIs were used earlier. They are not supported anymore.
* One version was released using alphavantage APIs but these APIs do not return the data reliably requiring retries.
* The latest version scrapes the bseindia and nseindia websites directly to get the real time market price of stocks.
* Other libraries like `csv, json, requests, decimal, collections, texttable` are used.

## Transactions File ##
* The first line of the file needs to contain the header given in the next line. It contains various fields that define a transaction.
* ___Symbol,Name,Type,Date,Shares,Price,Amount,Brokerage,STT,Charges,Receivable,Mode___
* Each line after the header represents a transaction with the transaction values specified in the same order as that of the header fields.
* ___The transactions should be listed in chronological order in this file___
* _Symbol_ - stock ticker value including the stock exchange informatio. For example, _NSE:VBL_ stands for _Varun Beverages_ in _NSE_, _BOM:500285_ stands for _Spicejet_ in _BSE_.
* _Name_ - name of the entity as given by the user
* _Type_ - value can be _Buy_ or _Sell_
* _Date_ - date of the transaction in _"MMM dd, YYYY"_ format.
* _Shares_ - number of shares involved in the transaction
* _Price_ - actual price of each share at which the transaction happened
* _Amount_ - this is the total amount involved in the transaction(_shares_ * _price_). For _Buy_ transactions, it is negative(money goes out) and for _Sell_ transactions, it is positive(money comes in).
* _Brokerage_ - actual brokerage incurred for the transaction
* _STT_ - Securities Transaction Tax imposed by the Indian Government for this transaction
* _Charges_ - all other charges for this transaction combined into this one component. This can include Stamp Duty, Transaction Charges, Service Charges and SEBI Turnover Tax.
* Receivable - This is the amount you will get after adjusting the _Amount_ for _Brokerage_, _STT_ and _Charges_. This is basically _Amount_ - (_Brokerage_ + _STT_ + _Charges_). You shell out more than what is required to buy the stock and you get lesser than the sale amount when you sell the stock
* Mode - This is the type of trade. Its value can be _del_ or _sqr_. _del_ stands for delivery mode/cash and carry, _sqr_ stands for intra-day square off trade

## Sample Transactions File (contents of `sample_portfolio.csv` in the repository has been reproduced here) ##
```
Symbol,Name,Type,Date,Shares,Price,Amount,Brokerage,STT,Charges,Receivable,Mode
NSE:VBL,Varun Beverages,Buy,"Apr 08, 2016",99,445,-44055,1.51,44,6.55,-44107.06,del
NSE:VBL,Varun Beverages,Sell,"Apr 17, 2017",99,403.45,39941.55,199.71,40,35.47,39666.37,del
BOM:540678,Cochin Shipyard,Buy,"Aug 10, 2017",30,411,-12330,0.01,12,3.31,-12345.32,del
BOM:540678,Cochin Shipyard,Sell,"Sep 10, 2017",30,311,9330,0.01,9,2.31,9318.68,del
BOM:540716,ICICI Lombard,Buy,"Sep 27, 2017",39,661,-25779,0.01,25,5.01,-25809.02,del
```
## Running the code ##
`
python equity_stats.py sample_portfolio.csv > output.txt
`

## Sample Output ##
* b_ - stands for buy; For example, b_date - buy date, b_charges - charges incurred during buy, b_value - buy value
* s_ - stands for sell; For example, s_date - sell date, b_charges - charges incurred during sell, s_value - sell value
* n_ - stands for net; n_charges - net charges (buy+sell), n_realized - net realized
* strg - short term realized gains, ltrg - long term realized gains
* h_value - holding value, h_charges - holding charges
* m_value - market value, m_price - market price
* a_price - average price, a_cost - average cost (cost = price + charges)
* u_gain - unit gain
* stug - short term unrealized gains, ltug - long term unrealized gains

```
PortFolio Realized Summmary
============================

+---------+---------+-----------+-----------+-----------+-----------+-----------+------------+----------+-----------+-----------+
|  name   | b_value |  s_value  | realized  | b_charges | s_charges | n_charges | n_realized | percent  |   strg    |   ltrg    |
+=========+=========+===========+===========+===========+===========+===========+============+==========+===========+===========+
| Cochin  | 12330   |      9330 |     -3000 |    15.320 |    11.320 |    26.640 |  -3026.640 | -24.547% | -3026.640 |         0 |
+---------+---------+-----------+-----------+-----------+-----------+-----------+------------+----------+-----------+-----------+
| Varun   | 44055   | 39941.550 | -4113.450 |    52.060 |   275.180 |   327.240 |  -4440.690 | -10.080% |         0 | -4440.690 |
+---------+---------+-----------+-----------+-----------+-----------+-----------+------------+----------+-----------+-----------+
| SUMMARY | 56385   | 49271.550 | -7113.450 |    67.380 |   286.500 |   353.880 |  -7467.330 | -13.243% | -3026.640 | -4440.690 |
+---------+---------+-----------+-----------+-----------+-----------+-----------+------------+----------+-----------+-----------+

PortFolio Holding Summmary
===========================

+---------+---------+-----------+--------+---------+---------+-----------+---------+--------+--------------+---------+---------+------+
|  name   | h_value |  m_value  | shares | a_price | m_price | h_charges | a_cost  | u_gain | n_unrealized | percent |  stug   | ltug |
+=========+=========+===========+========+=========+=========+===========+=========+========+==============+=========+=========+======+
| ICICI   | 25779   | 26744.250 |     39 |     661 | 685.750 |    30.020 | 661.770 | 23.980 |      935.230 |  3.628% | 935.230 |    0 |
+---------+---------+-----------+--------+---------+---------+-----------+---------+--------+--------------+---------+---------+------+
| SUMMARY | 25779   | 26744.250 |   *--* |    *--* |    *--* |    30.020 |    *--* |   *--* |      935.230 |  3.628% | 935.230 |    0 |
+---------+---------+-----------+--------+---------+---------+-----------+---------+--------+--------------+---------+---------+------+

ICICI Lombard (One Line Holding Summary)
=========================================

+---------+-----------+--------+---------+---------+-----------+---------+--------+--------------+---------+---------+------+
| h_value |  m_value  | shares | a_price | m_price | h_charges | a_cost  | u_gain | n_unrealized | percent |  stug   | ltug |
+=========+===========+========+=========+=========+===========+=========+========+==============+=========+=========+======+
| 25779   | 26744.250 |     39 |     661 | 685.750 |    30.020 | 661.770 | 23.980 |      935.230 |  3.628% | 935.230 |    0 |
+---------+-----------+--------+---------+---------+-----------+---------+--------+--------------+---------+---------+------+

ICICI Lombard (Holding Summary)
================================

+------------+--------+---------+---------+--------+---------+-----------+------------+-----------+---------+------+---------+
|   b_date   | shares | b_price | m_price | u_gain | h_value |  m_value  | unrealized | b_charges |  stug   | ltug | percent |
+============+========+=========+=========+========+=========+===========+============+===========+=========+======+=========+
| 2017-09-27 | 39     |     661 | 685.750 | 24.750 |   25779 | 26744.250 |    965.250 |    30.020 | 935.230 |    0 |  3.628% |
+------------+--------+---------+---------+--------+---------+-----------+------------+-----------+---------+------+---------+
| SUMMARY    | 39     |     661 | 685.750 | 24.750 |   25779 | 26744.250 |    965.250 |    30.020 | 935.230 |    0 |  3.628% |
+------------+--------+---------+---------+--------+---------+-----------+------------+-----------+---------+------+---------+

Cochin Shipyard (One Line Realized Summary)
============================================

+---------+---------+----------+-----------+-----------+-----------+------------+----------+-----------+------+
| b_value | s_value | realized | b_charges | s_charges | n_charges | n_realized | percent  |   strg    | ltrg |
+=========+=========+==========+===========+===========+===========+============+==========+===========+======+
| 12330   | 9330    |    -3000 |    15.320 |    11.320 |    26.640 |  -3026.640 | -24.547% | -3026.640 |    0 |
+---------+---------+----------+-----------+-----------+-----------+------------+----------+-----------+------+

Cochin Shipyard (Realized Summary)
===================================

+------------+------------+---------+---------+--------+--------+---------+---------+----------+-----------+-----------+-----------+-----------+------+----------+
|   b_date   |   s_date   | b_price | s_price | u_gain | shares | b_value | s_value | realized | b_charges | s_charges | n_charges |   strg    | ltrg | percent  |
+============+============+=========+=========+========+========+=========+=========+==========+===========+===========+===========+===========+======+==========+
| 2017-08-10 | 2017-09-10 |     411 |     311 |   -100 |     30 |   12330 |    9330 |    -3000 |    15.320 |    11.320 |    26.640 | -3026.640 |    0 | -24.547% |
+------------+------------+---------+---------+--------+--------+---------+---------+----------+-----------+-----------+-----------+-----------+------+----------+
| SUMMARY    | *--*       |     411 |     311 |   -100 |     30 |   12330 |    9330 |    -3000 |    15.320 |    11.320 |    26.640 | -3026.640 |    0 | -24.547% |
+------------+------------+---------+---------+--------+--------+---------+---------+----------+-----------+-----------+-----------+-----------+------+----------+

Varun Beverages (One Line Realized Summary)
============================================

+---------+-----------+-----------+-----------+-----------+-----------+------------+----------+------+-----------+
| b_value |  s_value  | realized  | b_charges | s_charges | n_charges | n_realized | percent  | strg |   ltrg    |
+=========+===========+===========+===========+===========+===========+============+==========+======+===========+
| 44055   | 39941.550 | -4113.450 |    52.060 |   275.180 |   327.240 |  -4440.690 | -10.080% |    0 | -4440.690 |
+---------+-----------+-----------+-----------+-----------+-----------+------------+----------+------+-----------+

Varun Beverages (Realized Summary)
===================================

+------------+------------+---------+---------+---------+--------+---------+-----------+-----------+-----------+-----------+-----------+------+-----------+----------+
|   b_date   |   s_date   | b_price | s_price | u_gain  | shares | b_value |  s_value  | realized  | b_charges | s_charges | n_charges | strg |   ltrg    | percent  |
+============+============+=========+=========+=========+========+=========+===========+===========+===========+===========+===========+======+===========+==========+
| 2016-04-08 | 2017-04-17 |     445 | 403.450 | -41.550 |     99 |   44055 | 39941.550 | -4113.450 |    52.060 |   275.180 |   327.240 |    0 | -4440.690 | -10.080% |
+------------+------------+---------+---------+---------+--------+---------+-----------+-----------+-----------+-----------+-----------+------+-----------+----------+
| SUMMARY    | *--*       |     445 | 403.450 | -41.550 |     99 |   44055 | 39941.550 | -4113.450 |    52.060 |   275.180 |   327.240 |    0 | -4440.690 | -10.080% |
+------------+------------+---------+---------+---------+--------+---------+-----------+-----------+-----------+-----------+-----------+------+-----------+----------+

```
