from collections import namedtuple
from datetime import datetime

from ibtax.currencies import CurrencyMap
from ibtax.utils import to_f


class Interest(
    namedtuple(
        "Interest",
        [
            "fees",
            "header",
            "raw_currency",
            "raw_date",
            "description",
            "raw_amount",
        ],
    )
):
    @property
    def currency(self):
        return self.raw_currency.upper()

    @property
    def datetime(self):
        return datetime.strptime(self.raw_date, "%Y-%m-%d")

    @property
    def amount(self):
        return abs(float(self.raw_amount))

    @classmethod
    def parse(cls, report):
        def walk():
            for row in report.rows:
                if (
                    row[0].lower() in ("interest", "процент")
                    and row[1].lower() == "data"
                    and row[2].lower() not in ("total", "всего")
                    and "total interest in usd" not in row[2].lower()
                    and "total in usd" not in row[2].lower()
                ):
                    yield cls(*row)

        return list(walk())


def to_row(currencies_map: CurrencyMap, fee):
    if fee.currency == "RUB":
        currency_rate = 1
    else:
        currency_rate = currencies_map.get(fee.currency, fee.datetime.date())

    amount_rub = currency_rate * fee.amount

    return [
        # date
        fee.datetime.strftime("%Y.%m.%d"),
        # amount usd
        to_f(fee.amount),
        # currency
        fee.currency,
        # currency rate
        to_f(currency_rate),
        # amount rub
        to_f(amount_rub),
        # tax to pay rub
        to_f(max(0, 0.13 * amount_rub)),
    ]


def show(w, currencies_map, report):
    items = Interest.parse(report)

    for item in items:
        w.writerow(to_row(currencies_map, item))
