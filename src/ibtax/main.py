import argparse
import csv
import logging
import pathlib
import re
import sys
from datetime import date

from ibtax import equities, dividends, fees, interest, lends
from ibtax.cache import PickleCache
from ibtax.currencies import CurrencyMap

cache_dir = pathlib.Path(__file__).parent.parent


class Report:
    def __init__(self, path):
        path = pathlib.Path(path)
        with path.open() as f:
            reader = csv.reader(f)
            self.rows = [r for r in reader]

        self.years = self._parse_years(self.rows)
        # take the last one, report could be a merged set of reports
        self.year = sorted(self.years)[-1]

    @property
    def period(self) -> (date, date):
        start_year = self.years[0]
        end_year = self.years[-1]
        return date(int(start_year), 1, 1), date(int(end_year), 12, 31)

    @staticmethod
    def _parse_years(rows):
        # Statement,Data,Period,"January 1, 2020 - December 31, 2020"
        def walk():
            for row in rows:
                if row[0].lower() == 'statement' and row[2].lower() == 'period':
                    val = row[3]
                    m = re.match(r'.+(\d\d\d\d).+(\d\d\d\d)', val)
                    if not m:
                        raise ValueError("can't find a report period year")
                    y1, y2 = m.group(1), m.group(2)
                    if y1 != y2:
                        raise ValueError("can't find a report period year")
                    yield y1

        return sorted(walk())


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

    report = Report(args.year_report)
    period_start, period_end = report.period

    cache = PickleCache(cache_dir)

    currencies_map = CurrencyMap.build(cache, period_start, period_end)

    w = csv.writer(sys.stdout)

    header('equity')
    equities.show(w, currencies_map, report)

    header('dividends')
    dividends.show(w, currencies_map, report)

    header('fees')
    fees.show(w, currencies_map, report)

    header('interest')
    interest.show(w, currencies_map, report)

    header('lend interest')
    lends.show(w, currencies_map, report)
