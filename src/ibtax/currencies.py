import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Iterable
from xml.dom import minidom

# https://www.cbr.ru/scripts/XML_val.asp?d=0
RQ_USD = 'R01235'
RQ_CAD = 'R01350'

CURRENCIES = dict(USD=RQ_USD, CAD=RQ_CAD)


def to_cb_date_format(dt):
    return dt.strftime("%d/%m/%Y")


@dataclass
class CurrencyRatio:
    day: date
    value: float


def load_currency(rq, start, end):
    start = to_cb_date_format(start)
    end = to_cb_date_format(end)

    url = f'https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={start}&date_req2={end}&VAL_NM_RQ={rq}'
    f = urllib.request.urlopen(url)
    contents = f.read().decode('utf-8')

    dom = minidom.parseString(contents)
    root = dom.getElementsByTagName("ValCurs")[0]

    def walk():
        for node in root.getElementsByTagName("Record"):
            value = node.getElementsByTagName("Value")[0].firstChild.nodeValue
            value = float(value.replace(',', '.'))

            date_str = node.attributes['Date'].value
            d = datetime.strptime(date_str, "%d.%m.%Y").date()
            yield CurrencyRatio(d, value)

    return list(walk())


def fill_gaps(seq):
    mem = dict(cur=seq[0])

    def walk():
        yield seq[0]

        for cur in seq[1:]:
            prev_date = mem['cur'].day
            prev_value = mem['cur'].value

            diff = (cur.day - prev_date).days
            for i in range(1, diff):
                yield CurrencyRatio(prev_date + timedelta(days=i),
                                    prev_value)

            yield cur
            mem['cur'] = cur

    return list(walk())


def prepare_currency(cache, rq, start, end):
    key_name = f'.{rq}.{start}-{end}.pickle'

    cached = cache.get(key_name)
    if cached:
        return cached

    seq = load_currency(rq, start, end)
    seq = fill_gaps(seq)

    cache.set(key_name, seq)

    return seq


class CurrencyMap:
    def __init__(self, self_cur):
        self.__map = {}
        self.__self_cur = self_cur

    def add(self, cur: str, seq: Iterable[CurrencyRatio]):
        self.__map[cur] = {x.day: x.value for x in seq}

    def get(self, cur: str, day: date) -> float:
        if cur == self.__self_cur:
            return 1.0
        return self.__map[cur][day]

    @classmethod
    def build(cls, cache, start, end) -> "CurrencyMap":
        m = cls("RUB")

        for name, rq in CURRENCIES.items():
            seq = prepare_currency(cache, rq, start, end)
            m.add(name, seq)

        return m
