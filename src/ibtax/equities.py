import logging
from collections import namedtuple, defaultdict
from datetime import datetime

from ibtax.currencies import CurrencyMap
from ibtax.utils import to_f4, to_f

logger = logging.getLogger(__name__)


class Trade(
    namedtuple(
        "Trade",
        [
            "type",
            "header",
            "data_discriminator",
            "asset_category",
            "raw_currency",
            "symbol",
            "raw_datetime",
            "raw_quantity",
            "raw_t_price",
            "c_price",
            "proceeds",
            "raw_comm_fee",
            "basis",
            "raw_realized_pl",
            "mtm_pl",
            "code",
        ],
    )
):
    @property
    def quantity(self):
        # splits may contain non integer values
        try:
            return int(self.raw_quantity)
        except ValueError:
            logger.warning("unexpected quantity in a trade %s", self)
            return int(float(self.raw_quantity))

    @property
    def realized_pl(self):
        return float(self.raw_realized_pl or 0)

    @property
    def datetime(self):
        return datetime.strptime(self.raw_datetime, "%Y-%m-%d, %H:%M:%S")

    @property
    def currency(self):
        return self.raw_currency.upper()

    @property
    def t_price(self):
        return float(self.raw_t_price)

    @property
    def comm_fee(self):
        return float(self.raw_comm_fee)

    @classmethod
    def parse(cls, report):
        def walk():
            for row in report.rows:
                if row[0].lower() == "trades" and row[1].lower() == "data":
                    yield cls(*row)

        return list(walk())


class SymbolTrades:
    def __init__(self, symbol, trades):
        self.symbol = symbol
        self.trades = trades

    def __repr__(self):
        return "{}".format(self.symbol)

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

    return [
        SymbolTrades(symbol, trades) for symbol, trades in sorted(res.items())
    ]


class QuantityOrder:
    def __init__(self, quantity, trade):
        self.quantity = quantity
        self.trade = trade


class TakeProfit:
    def __init__(self, buys, sell):
        self.buys = buys
        self.sell = sell

    @property
    def year(self):
        return str(self.sell.datetime.year)


def to_rows(currencies: CurrencyMap, take_profit):
    symbol = take_profit.sell.symbol

    def walk():
        agg = dict(buy=0, buy_rub=0, fee=0, fee_rub=0)

        for q_order in take_profit.buys:
            trade = q_order.trade

            currency_rate = currencies.get(
                trade.currency, trade.datetime.date()
            )

            cost = abs(trade.t_price * q_order.quantity)
            agg["buy"] += cost

            cost_rub = currency_rate * cost
            agg["buy_rub"] += cost_rub

            fee = abs(trade.comm_fee)
            agg["fee"] += fee

            fee_rub = currency_rate * fee
            agg["fee_rub"] += fee_rub

            yield [
                # symbol
                symbol,
                # date
                trade.datetime.strftime("%Y.%m.%d"),
                # quantity
                q_order.quantity,
                # price
                to_f4(trade.t_price),
                # cost
                to_f(-cost),
                # currency
                trade.currency,
                # currency rate
                to_f(currency_rate),
                # cost in rub
                to_f(-cost_rub),
                # fee
                to_f(-fee),
                # fee in rub
                to_f(-fee_rub),
            ]

        trade = take_profit.sell
        currency_rate = currencies.get(trade.currency, trade.datetime.date())

        fee = abs(trade.comm_fee)
        agg["fee"] += fee

        fee_rub = currency_rate * fee
        agg["fee_rub"] += fee_rub

        cost = abs(trade.t_price * trade.quantity)
        cost_rub = currency_rate * cost
        yield [
            # symbol
            symbol,
            # date
            trade.datetime.strftime("%Y.%m.%d"),
            # quantity
            -abs(trade.quantity),
            # price
            to_f4(trade.t_price),
            # cost
            to_f(cost),
            # currency
            trade.currency,
            # currency rate
            to_f(currency_rate),
            # cost in rub
            to_f(cost_rub),
            # fee
            to_f(-fee),
            # fee in rub
            to_f(-fee_rub),
            # pl
            to_f(trade.realized_pl),
            # pl in rub
            to_f(cost_rub - agg["buy_rub"]),
            # tax baseline in rub
            to_f(cost_rub - agg["buy_rub"] - agg["fee_rub"]),
        ]

    return list(walk())


def take_profits(symb):
    def walk():
        buy_trades = [QuantityOrder(x.quantity, x) for x in symb.buy_trades()]

        for sell in symb.sell_trades():
            quantity = -sell.quantity

            buys = []

            while buy_trades:
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


def show(w, currencies_map, report):
    grouped = group_trades(Trade.parse(report))
    for symb in grouped:
        if not symb.has_realised():
            continue

        for take_profit in take_profits(symb):
            if take_profit.year != report.year:
                continue

            for row in to_rows(currencies_map, take_profit):
                w.writerow(row)
