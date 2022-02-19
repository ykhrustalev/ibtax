from dataclasses import dataclass
from datetime import datetime

from ibtax.currencies import CurrencyMap
from ibtax.utils import to_f


@dataclass
class LendInterest:
    title: str
    header: str
    raw_currency: str
    raw_value_date: str
    symbol: str
    raw_start_date: str
    raw_quantity: str
    raw_collateral_amount: str
    raw_interest_rate_by_ib: str
    raw_interest_paid_to_ib: str
    raw_interest_rate_on_customer: str
    raw_interest_paid_to_customer: str
    code: str

    @property
    def currency(self):
        return self.raw_currency.upper()

    @property
    def datetime(self):
        return datetime.strptime(self.raw_start_date, '%Y-%m-%d')

    @property
    def quantity(self):
        return int(self.raw_quantity)

    @property
    def amount(self):
        return float(self.raw_interest_paid_to_customer)

    @classmethod
    def parse(cls, report):
        def walk():
            for row in report.rows:
                if (
                    'ibkr managed securities lent interest details'
                    ' (stock yield enhancement program)' in row[0].lower() and
                    row[1].lower() == 'data' and
                    'total' not in row[2].lower()
                ):
                    yield cls(*row)

        return list(walk())


def to_row(currencies_map: CurrencyMap, item):
    currency_rate = currencies_map.get(item.currency, item.datetime.date())

    amount_rub = currency_rate * item.amount

    return [
        # date
        item.datetime.strftime('%Y.%m.%d'),
        # symbol
        item.symbol,
        # amount usd
        to_f(item.amount),
        # currency
        item.currency,
        # currency rate
        to_f(currency_rate),
        # amount rub
        to_f(amount_rub),
        # tax to pay rub
        to_f(max(0, 0.13 * amount_rub))
    ]


def show(w, currencies_map, report):
    items = LendInterest.parse(report)

    for item in items:
        if item.amount > 0:
            w.writerow(to_row(currencies_map, item))
