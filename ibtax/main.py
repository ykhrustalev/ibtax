import csv
import pathlib
import sys
from collections import namedtuple, defaultdict
from datetime import date, datetime

from ibtax.cache import PickleCache
from ibtax.currencies import get_currencies_map


class Trade(namedtuple('Trade', [
    'type', 'header', 'data_discriminator', 'asset_category', 'raw_currency',
    'symbol', 'raw_datetime', 'raw_quantity', 'raw_t_price', 'c_price', 'proceeds',
    'raw_comm_fee', 'basis', 'raw_realized_pl', 'mtm_pl', 'code'
])):
    @property
    def quantity(self):
        return int(self.raw_quantity)

    @property
    def realized_pl(self):
        return float(self.raw_realized_pl or 0)

    @property
    def datetime(self):
        return datetime.strptime(self.raw_datetime, '%Y-%m-%d, %H:%M:%S')

    @property
    def currency(self):
        return self.raw_currency.upper()

    @property
    def t_price(self):
        return float(self.raw_t_price)

    @property
    def comm_fee(self):
        return float(self.raw_comm_fee)


RQ_USD = 'R01235'
RQ_CAD = 'R01350'


def to_f(v):
    if isinstance(v, float):
        return '{:.2f}'.format(v).replace('.', ',')
    return str(v).replace('.', ',')


class Report:
    def __init__(self, path):
        path = pathlib.Path(path)
        with path.open() as f:
            reader = csv.reader(f)
            self.rows = [r for r in reader]

    def trades(self):
        def walk():
            for row in self.rows:
                if row[0].lower() == 'trades' and row[1].lower() == 'data':
                    yield Trade(*row)

        return list(walk())


class SymbolTrades:
    def __init__(self, symbol, trades):
        self.symbol = symbol
        self.trades = trades

    def __repr__(self):
        return '{}'.format(self.symbol)

    def has_realised(self):
        for trade in self.trades:
            if abs(trade.realized_pl) > 0.001:
                return True

        return False

    def buy_trades(self):
        return [t for t in self.trades if t.quantity > 0]

    def sell_trades(self):
        return [t for t in self.trades if t.quantity < 0]


def group_trades(trades):
    res = defaultdict(list)
    for trade in trades:
        res[trade.symbol].append(trade)

    return [SymbolTrades(symbol, trades)
            for symbol, trades in sorted(res.items())]


class QuantityOrder:
    def __init__(self, quantity, trade):
        self.quantity = quantity
        self.trade = trade


class TakeProfit:
    def __init__(self, buys, sell):
        self.buys = buys
        self.sell = sell


def to_rows(currencies, take_profit):
    symbol = take_profit.sell.symbol

    def walk():
        costs = dict(
            buy=0,
            buy_exchanged=0,
            fee=0,
            fee_exchanged=0
        )

        for q_order in take_profit.buys:
            trade = q_order.trade

            currency_rate = currencies[trade.currency][trade.datetime.date()]

            buy_cost = trade.t_price * q_order.quantity
            costs['buy'] += buy_cost

            buy_exchanged = currency_rate * q_order.quantity
            costs['buy_exchanged'] += buy_exchanged

            costs['fee'] += trade.comm_fee

            fee_exchanged = currency_rate * trade.comm_fee
            costs['fee_exchanged'] += fee_exchanged

            yield [
                symbol,
                trade.datetime.strftime('%Y.%m.%d'),
                q_order.quantity,
                to_f(trade.t_price),
                to_f(buy_cost),
                trade.currency,
                to_f(currency_rate),
                to_f(buy_exchanged),
                to_f(trade.comm_fee),
                to_f(fee_exchanged),
                ''

            ]

        trade = take_profit.sell
        currency_rate = currencies[trade.currency][trade.datetime.date()]

        realized_pl_exchanged = currency_rate * trade.realized_pl

        costs['fee'] += trade.comm_fee

        fee_exchanged = currency_rate * trade.comm_fee
        costs['fee_exchanged'] += fee_exchanged

        yield [
            symbol,
            trade.datetime.strftime('%Y.%m.%d'),
            trade.quantity,
            to_f(trade.t_price),
            to_f(trade.t_price * trade.quantity),
            trade.currency,
            to_f(currency_rate),
            to_f(currency_rate * trade.quantity),
            to_f(trade.comm_fee),
            to_f(fee_exchanged),
            to_f(trade.realized_pl),
            to_f(realized_pl_exchanged),
            # tax base
            to_f(realized_pl_exchanged - costs['buy_exchanged'] + costs['fee_exchanged']),
        ]

    return list(walk())


def take_profits(symb):
    def walk():
        buy_trades = [QuantityOrder(x.quantity, x) for x in symb.buy_trades()]

        for sell in symb.sell_trades():
            quantity = -sell.quantity

            buys = []

            while True:
                buy = buy_trades.pop(0)

                if buy.quantity == quantity:
                    buys.append(QuantityOrder(quantity, buy.trade))
                    break

                if buy.quantity > quantity:
                    buys.append(QuantityOrder(quantity, buy.trade))
                    extra = buy.quantity - quantity
                    buy_trades.insert(0, QuantityOrder(extra, buy.trade))
                    break

                buys.append(QuantityOrder(buy.quantity, buy.trade))
                quantity -= buy.quantity

            yield TakeProfit(buys, sell)

    return list(walk())


def main(report_path):
    cur_map = dict(USD=RQ_USD, CAD=RQ_CAD)
    start, end = date(2017, 12, 10), date(2018, 12, 31)

    cache = PickleCache()

    currencies_map = get_currencies_map(cache, cur_map, start, end)

    report = Report(report_path)
    trades = report.trades()

    grouped = group_trades(trades)

    w = csv.writer(sys.stdout)

    for symb in grouped:
        if symb.has_realised():
            for take_profit in take_profits(symb):
                # print()
                # print(symb.symbol)
                # print([(x.quantity, x.trade) for x in take_profit.buys])
                # print(take_profit.sell)

                for row in to_rows(currencies_map, take_profit):
                    w.writerow(row)

    #
    # for trade in trades:
    #     if trade.realized_pl and abs(float(trade.realized_pl)) > 0.001:
    #         row = [fix(i) for i in trade]
    #         w.writerow(row)


if __name__ == '__main__':
    main('../report.csv')
