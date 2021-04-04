import csv
import logging
import pathlib
import re
import sys
from datetime import date
import argparse

from ibtax import equities, dividends, fees, interest
from ibtax.cache import PickleCache
from ibtax.currencies import get_currencies_map

RQ_USD = 'R01235'
RQ_CAD = 'R01350'

CURRENCIES = dict(USD=RQ_USD, CAD=RQ_CAD)

START, END = date(2017, 12, 10), date(2020, 12, 31)


class Report:
    def __init__(self, path):
        path = pathlib.Path(path)
        with path.open() as f:
            reader = csv.reader(f)
            self.rows = [r for r in reader]

        self.year = self._parse_year(self.rows)

    @staticmethod
    def _parse_year(rows):
        # Statement,Data,Period,"January 1, 2020 - December 31, 2020"
        for row in rows:
            if row[0].lower() == 'statement' and row[2].lower() == 'period':
                val = row[3]
                m = re.match(r'.+(\d\d\d\d).+(\d\d\d\d)', val)
                if not m:
                    raise ValueError("can't find a report period year")
                y1, y2 = m.group(1), m.group(2)
                if y1 != y2:
                    raise ValueError("can't find a report period year")
                return y1


def header(title):
    print('#' * 79)
    print("# {}".format(title))
    print('#' * 79)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--year-report', help='year report')
    args = parser.parse_args()
    return args


def main():
    logging.basicConfig()

    args = parse_args()

    cache = PickleCache()

    currencies_map = get_currencies_map(cache, CURRENCIES, START, END)

    report = Report(args.year_report)

    w = csv.writer(sys.stdout)

    header('equity')
    equities.show(w, currencies_map, report)

    header('dividends')
    dividends.show(w, currencies_map, report)

    header('fees')
    fees.show(w, currencies_map, report)

    header('interest')
    interest.show(w, currencies_map, report)
