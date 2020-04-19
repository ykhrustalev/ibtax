import csv
import pathlib
import sys
from datetime import date

from ibtax import equities, dividends, fees, interest
from ibtax.cache import PickleCache
from ibtax.currencies import get_currencies_map

RQ_USD = 'R01235'
RQ_CAD = 'R01350'

CURRENCIES = dict(USD=RQ_USD, CAD=RQ_CAD)

START, END = date(2017, 12, 10), date(2019, 12, 31)


class Report:
    def __init__(self, path):
        path = pathlib.Path(path)
        with path.open() as f:
            reader = csv.reader(f)
            self.rows = [r for r in reader]


def header(title):
    print('#' * 79)
    print("# {}".format(title))
    print('#' * 79)


def main():
    report_path = sys.argv[1]

    cache = PickleCache()

    currencies_map = get_currencies_map(cache, CURRENCIES, START, END)

    report = Report(report_path)

    w = csv.writer(sys.stdout)

    header('equity')
    equities.show(w, currencies_map, report)

    header('dividends')
    dividends.show(w, currencies_map, report)

    header('fees')
    fees.show(w, currencies_map, report)

    header('interest')
    interest.show(w, currencies_map, report)
