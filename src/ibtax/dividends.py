import logging
import re
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime

from ibtax.currencies import CurrencyMap
from ibtax.formatting import to_f

logger = logging.getLogger(__name__)


def parse_symbol(value):
    # FNCL (US3160925018) Cash Dividend 0.19100000 USD per Share (Ordinary Dividend)  # noqa
    return re.match(r"^(?P<symbol>\w+)\s*\(.*", value).group("symbol")


class Payout(
    namedtuple(
        "Payout",
        [
            "dividends",
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

    @property
    def symbol(self):
        return parse_symbol(self.description)

    @classmethod
    def parse(cls, report):
        def walk():
            for row in report.rows:
                if (
                    row[0].lower() == "dividends"
                    and row[1].lower() == "data"
                    and "total" not in row[2].lower()
                    and report.year in row[3].lower()
                ):
                    yield cls(*row)

        return list(walk())


@dataclass
class Withhold:
    withholding_tax: str
    header: str
    raw_currency: str
    raw_date: str
    description: str
    raw_amount: str
    code: str

    @classmethod
    def blank(cls):
        return cls(
            withholding_tax="",
            header="",
            raw_currency="",
            raw_date="",
            description="",
            raw_amount="0",
            code="",
        )

    @property
    def currency(self):
        return self.raw_currency.upper()

    @property
    def datetime(self):
        return datetime.strptime(self.raw_date, "%Y-%m-%d")

    @property
    def amount(self):
        return abs(float(self.raw_amount))

    @property
    def symbol(self):
        return parse_symbol(self.description)

    @classmethod
    def parse(cls, report):
        def walk():
            for row in report.rows:
                if (
                    row[0].lower() == "withholding tax"
                    and row[1].lower() == "data"
                    and "total" not in row[2].lower()
                    and report.year in row[3].lower()
                ):
                    yield cls(*row)

        return list(walk())


@dataclass
class Event:
    payout: Payout
    withhold: Withhold


def get_events(report):
    payouts = Payout.parse(report)
    withholds = Withhold.parse(report)

    def walk():
        for p in payouts:
            w = None

            while withholds:
                w = withholds.pop(0)
                if p.symbol == w.symbol:
                    # drop those that are not matching
                    break
                logger.warning("skipping %s", w)

            if w is None:
                logger.warning(f"can't match withhold for {p}")
                w = Withhold.blank()

            yield Event(p, w)

    return list(walk())


def to_row(currencies_map: CurrencyMap, event):
    p = event.payout
    w = event.withhold

    currency_rate = currencies_map.get(p.currency, p.datetime.date())

    amount_rub = currency_rate * p.amount
    tax_paid_rub = currency_rate * w.amount

    return [
        # symb
        p.symbol,
        # date
        p.datetime.strftime("%Y.%m.%d"),
        # amount usd
        to_f(p.amount),
        # currency
        p.currency,
        # currency rate
        to_f(currency_rate),
        # tab base rub
        to_f(amount_rub),
        # tax payed usd
        to_f(w.amount),
        # tax payed rub
        to_f(tax_paid_rub),
        # tax to pay rub
        to_f(max(0, 0.13 * amount_rub - tax_paid_rub)),
    ]


def show(w, currencies_map, report):
    events = get_events(report)

    for event in events:
        w.writerow(to_row(currencies_map, event))
