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
* One version was released using alphavantage APIs but these APIs do not return the data reliably even with retries.
* The latest version scrapes the bseindia and nseindia websites directly to get the real time market price of stocks.
* Other libraries used are: `csv, json, requests, decimal, collections, texttable`

## Transactions File ##
* The first line of the file needs to contain the header given in the next line. It contains various fields that define a transaction.
* ___Symbol,Name,Type,Date,Shares,Price,Amount,Brokerage,STT,Charges,Receivable,Mode___
* Each line after the header represents a transaction with the transaction values specified in the same order as that of the header fields.
* ___The transactions should be listed in chronological order in this file___
* _Symbol_ - stock ticker value including the stock exchange informatio. For example, _NSE:VBL_ stands for _Varun Beverages_ in _NSE_, _BSE:500285_ stands for _Spicejet_ in _BSE_.
* _Name_ - name of the entity as given by the user
* _Type_ - value can be _Buy_ or _Sell_. We can have additional entries in the transactions file for Dividend, CashIn, CashOut to track dividend received and capital coming in and going out of the demat account.
* _Date_ - date of the transaction in _"MMM dd, YYYY"_ format.
* _Shares_ - number of shares involved in the transaction
* _Price_ - actual price of each share at which the transaction happened
* _Amount_ - this is the total amount involved in the transaction(_shares_ * _price_). For _Buy_ transactions, it is negative(money goes out) and for _Sell_ transactions, it is positive(money comes in).
* _Brokerage_ - actual brokerage incurred for the transaction
* _STT_ - Securities Transaction Tax imposed by the Indian Government for this transaction
* _Charges_ - all other charges for this transaction combined into this one component. This can include Stamp Duty, Transaction Charges, Service Charges and SEBI Turnover Tax.
* Receivable - This is the amount you will get after adjusting the _Amount_ for _Brokerage_, _STT_ and _Charges_. This is basically _Amount_ - (_Brokerage_ + _STT_ + _Charges_). You shell out more than what is required to buy the stock and you get lesser than the sale amount when you sell the stock
* Mode - This is the mode through which the trade is carried out. Its value can be _del_ or _sqr_. _del_ stands for delivery mode/cash and carry, _sqr_ stands for intra-day square off trade

## Sample Transactions File (contents of `sample_portfolio.csv` in the repository has been reproduced here) ##
```
Symbol,Name,Type,Date,Shares,Price,Amount,Brokerage,STT,Charges,Receivable,Mode
NSE:VBL,Varun Beverages,Buy,"Apr 08, 2016",99,445,-44055,1.51,44,6.55,-44107.06,del
NSE:VBL,Varun Beverages,Sell,"Apr 17, 2017",99,403.45,39941.55,199.71,40,35.47,39666.37,del
BSE:540678,Cochin Shipyard,Buy,"Aug 10, 2016",30,411,-12330,0.01,12,3.31,-12345.32,del
BSE:540678,Cochin Shipyard,Sell,"Apr 10, 2018",30,511,15330,0.01,9,2.31,15318.68,del
BSE:540716,ICICI Lombard,Buy,"Feb 27, 2017",39,661,-25779,0.01,25,5.01,-25809.02,del
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
* h_value - holding value, h_charges - holding charges, j_price - price on Jan 31, 2018
* m_value - market value, m_price - market price
* u_pgain - unit gain w.r.t the b_price, u_cgain - unit gain w.r.t the b_cost
* stg - short term gains, ltg - long term gains, xltg - taxable long term gains

```
Varun Beverages (Realized Details)
===================================

+------------+------------+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+---------+-----+-----------+-----------+
|   b_date   |   s_date   | shares | b_value |  s_value  | b_price | s_price | u_pgain |  g_gain   | b_charges | b_cost  | u_cgain | s_charges | n_charges |  n_gain   | percent | j_price | x_price | stg |    ltg    |   xltg    |
+============+============+========+=========+===========+=========+=========+=========+===========+===========+=========+=========+===========+===========+===========+=========+=========+=========+=====+===========+===========+
| 2016-04-08 | 2017-04-17 |     99 |   44055 | 39941.550 |     445 | 403.450 | -41.550 | -4113.450 |    52.060 | 445.526 | -42.076 |   275.180 |   327.240 | -4440.690 | -10.080 |       0 |     445 |   0 | -4440.690 | -4440.690 |
+------------+------------+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+---------+-----+-----------+-----------+
| *--*       | *--*       |     99 |   44055 | 39941.550 |     445 | 403.450 | -41.550 | -4113.450 |    52.060 | 445.526 | -42.076 |   275.180 |   327.240 | -4440.690 | -10.080 |       0 |     445 |   0 | -4440.690 | -4440.690 |
+------------+------------+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+---------+-----+-----------+-----------+

Varun Beverages (One Line Realized Summary)
============================================

+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+-----+-----------+-----------+
| shares | b_value |  s_value  | b_price | s_price | u_pgain |  g_gain   | b_charges | b_cost  | u_cgain | s_charges | n_charges |  n_gain   | percent | j_price | stg |    ltg    |   xltg    |
+========+=========+===========+=========+=========+=========+===========+===========+=========+=========+===========+===========+===========+=========+=========+=====+===========+===========+
| 99     | 44055   | 39941.550 |     445 | 403.450 | -41.550 | -4113.450 |    52.060 | 445.526 | -42.076 |   275.180 |   327.240 | -4440.690 | -10.080 |       0 |   0 | -4440.690 | -4440.690 |
+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+-----+-----------+-----------+

Cochin Shipyard (Realized Details)
===================================

+------------+------------+--------+---------+---------+---------+---------+---------+--------+-----------+---------+---------+-----------+-----------+----------+---------+---------+---------+-----+----------+----------+
|   b_date   |   s_date   | shares | b_value | s_value | b_price | s_price | u_pgain | g_gain | b_charges | b_cost  | u_cgain | s_charges | n_charges |  n_gain  | percent | j_price | x_price | stg |   ltg    |   xltg   |
+============+============+========+=========+=========+=========+=========+=========+========+===========+=========+=========+===========+===========+==========+=========+=========+=========+=====+==========+==========+
| 2016-08-10 | 2018-02-10 |     30 |   12330 |   15330 |     411 |     511 |     100 |   3000 |    15.320 | 411.511 |  99.489 |    11.320 |    26.640 | 2973.360 |  24.115 |       0 |     411 |   0 | 2973.360 | 2973.360 |
+------------+------------+--------+---------+---------+---------+---------+---------+--------+-----------+---------+---------+-----------+-----------+----------+---------+---------+---------+-----+----------+----------+
| *--*       | *--*       |     30 |   12330 |   15330 |     411 |     511 |     100 |   3000 |    15.320 | 411.511 |  99.489 |    11.320 |    26.640 | 2973.360 |  24.115 |       0 |     411 |   0 | 2973.360 | 2973.360 |
+------------+------------+--------+---------+---------+---------+---------+---------+--------+-----------+---------+---------+-----------+-----------+----------+---------+---------+---------+-----+----------+----------+

Cochin Shipyard (One Line Realized Summary)
============================================

+--------+---------+---------+---------+---------+---------+--------+-----------+---------+---------+-----------+-----------+----------+---------+---------+-----+----------+----------+
| shares | b_value | s_value | b_price | s_price | u_pgain | g_gain | b_charges | b_cost  | u_cgain | s_charges | n_charges |  n_gain  | percent | j_price | stg |   ltg    |   xltg   |
+========+=========+=========+=========+=========+=========+========+===========+=========+=========+===========+===========+==========+=========+=========+=====+==========+==========+
| 30     | 12330   |   15330 |     411 |     511 |     100 |   3000 |    15.320 | 411.511 |  99.489 |    11.320 |    26.640 | 2973.360 |  24.115 |       0 |   0 | 2973.360 | 2973.360 |
+--------+---------+---------+---------+---------+---------+--------+-----------+---------+---------+-----------+-----------+----------+---------+---------+-----+----------+----------+

ICICI Lombard (Holding Details)
================================

+------------+--------+---------+-----------+---------+---------+---------+----------+-----------+---------+---------+-----------+-----------+----------+---------+---------+---------+-----+----------+---------+
|   b_date   | shares | b_value |  s_value  | b_price | s_price | u_pgain |  g_gain  | b_charges | b_cost  | u_cgain | s_charges | n_charges |  n_gain  | percent | j_price | x_price | stg |   ltg    |  xltg   |
+============+========+=========+===========+=========+=========+=========+==========+===========+=========+=========+===========+===========+==========+=========+=========+=========+=====+==========+=========+
| 2017-02-27 | 39     |   25779 | 29922.750 |     661 | 767.250 | 106.250 | 4143.750 |    30.020 | 661.770 | 105.480 |         0 |    30.020 | 4113.730 |  15.958 |     787 | 767.250 |   0 | 4113.730 | -30.020 |
+------------+--------+---------+-----------+---------+---------+---------+----------+-----------+---------+---------+-----------+-----------+----------+---------+---------+---------+-----+----------+---------+
| *--*       | 39     |   25779 | 29922.750 |     661 | 767.250 | 106.250 | 4143.750 |    30.020 | 661.770 | 105.480 |         0 |    30.020 | 4113.730 |  15.958 |     787 | 767.250 |   0 | 4113.730 | -30.020 |
+------------+--------+---------+-----------+---------+---------+---------+----------+-----------+---------+---------+-----------+-----------+----------+---------+---------+---------+-----+----------+---------+

ICICI Lombard (One Line Holding Summary)
=========================================

+--------+---------+-----------+---------+---------+---------+----------+-----------+---------+---------+-----------+-----------+----------+---------+---------+-----+----------+---------+
| shares | b_value |  s_value  | b_price | s_price | u_pgain |  g_gain  | b_charges | b_cost  | u_cgain | s_charges | n_charges |  n_gain  | percent | j_price | stg |   ltg    |  xltg   |
+========+=========+===========+=========+=========+=========+==========+===========+=========+=========+===========+===========+==========+=========+=========+=====+==========+=========+
| 39     | 25779   | 29922.750 |     661 | 767.250 | 106.250 | 4143.750 |    30.020 | 661.770 | 105.480 |         0 |    30.020 | 4113.730 |  15.958 |     787 |   0 | 4113.730 | -30.020 |
+--------+---------+-----------+---------+---------+---------+----------+-----------+---------+---------+-----------+-----------+----------+---------+---------+-----+----------+---------+

PortFolio Realized Summmary
============================

+--------+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+-----+-----------+-----------+
|  name  | shares | b_value |  s_value  | b_price | s_price | u_pgain |  g_gain   | b_charges | b_cost  | u_cgain | s_charges | n_charges |  n_gain   | percent | j_price | stg |    ltg    |   xltg    |
+========+========+=========+===========+=========+=========+=========+===========+===========+=========+=========+===========+===========+===========+=========+=========+=====+===========+===========+
| Varun  | 99     |   44055 | 39941.550 |     445 | 403.450 | -41.550 | -4113.450 |    52.060 | 445.526 | -42.076 |   275.180 |   327.240 | -4440.690 | -10.080 |       0 |   0 | -4440.690 | -4440.690 |
+--------+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+-----+-----------+-----------+
| Cochin | 30     |   12330 |     15330 |     411 |     511 |     100 |      3000 |    15.320 | 411.511 |  99.489 |    11.320 |    26.640 |  2973.360 |  24.115 |       0 |   0 |  2973.360 |  2973.360 |
+--------+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+-----+-----------+-----------+
| *--*   | *--*   |   56385 | 55271.550 |    *--* |    *--* |    *--* | -1113.450 |    67.380 |    *--* |    *--* |   286.500 |   353.880 | -1467.330 |  -2.602 |    *--* |   0 | -1467.330 | -1467.330 |
+--------+--------+---------+-----------+---------+---------+---------+-----------+-----------+---------+---------+-----------+-----------+-----------+---------+---------+-----+-----------+-----------+

PortFolio Holding Summmary
===========================

+-------+--------+---------+-----------+---------+---------+---------+----------+-----------+---------+---------+-----------+-----------+----------+---------+---------+-----+----------+---------+
| name  | shares | b_value |  s_value  | b_price | s_price | u_pgain |  g_gain  | b_charges | b_cost  | u_cgain | s_charges | n_charges |  n_gain  | percent | j_price | stg |   ltg    |  xltg   |
+=======+========+=========+===========+=========+=========+=========+==========+===========+=========+=========+===========+===========+==========+=========+=========+=====+==========+=========+
| ICICI | 39     |   25779 | 29922.750 |     661 | 767.250 | 106.250 | 4143.750 |    30.020 | 661.770 | 105.480 |         0 |    30.020 | 4113.730 |  15.958 |     787 |   0 | 4113.730 | -30.020 |
+-------+--------+---------+-----------+---------+---------+---------+----------+-----------+---------+---------+-----------+-----------+----------+---------+---------+-----+----------+---------+
| *--*  | *--*   |   25779 | 29922.750 |    *--* |    *--* |    *--* | 4143.750 |    30.020 |    *--* |    *--* |         0 |    30.020 | 4113.730 |  15.958 |    *--* |   0 | 4113.730 | -30.020 |
+-------+--------+---------+-----------+---------+---------+---------+----------+-----------+---------+---------+-----------+-----------+----------+---------+---------+-----+----------+---------+

```
