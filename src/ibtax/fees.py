from collections import namedtuple
from datetime import datetime

from ibtax.currencies import CurrencyMap
from ibtax.formatting import to_f


class Fee(
    namedtuple(
        "Fee",
        [
            "fees",
            "header",
            "subtitle",
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
                    row[0].lower() == "fees"
                    and row[1].lower() == "data"
                    and "total" not in row[2].lower()
                ):
                    yield cls(*row)

        return list(walk())


def to_row(currencies_map: CurrencyMap, fee):
    currency_rate = currencies_map.get(fee.currency, fee.datetime.date())

    return [
        # date
        fee.datetime.strftime("%Y.%m.%d"),
        # description
        fee.description,
        # amount usd
        to_f(fee.amount),
        # currency
        fee.currency,
        # currency rate
        to_f(currency_rate),
        # amount rub
        to_f(currency_rate * fee.amount),
    ]


def show(w, currencies_map, report):
    fees = Fee.parse(report)

    for fee in fees:
        w.writerow(to_row(currencies_map, fee))
