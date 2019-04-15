import urllib.parse
import urllib.request
from collections import namedtuple
from datetime import datetime, timedelta
from xml.dom import minidom


def to_cb_date_format(dt):
    return dt.strftime("%d/%m/%Y")


CurrencyCourse = namedtuple('CurrencyCourse', ['date', 'value'])


def load_currency(rq, start, end):
    start = to_cb_date_format(start)
    end = to_cb_date_format(end)

    url = 'http://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={start}&date_req2={end}&VAL_NM_RQ={rq}'.format(
        start=start,
        end=end,
        rq=rq,
    )
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
            yield CurrencyCourse(d, value)

    return list(walk())


def fill_gaps(seq):
    mem = dict(cur=seq[0])

    def walk():
        yield seq[0]

        for cur in seq[1:]:
            prev_date = mem['cur'].date
            prev_value = mem['cur'].value

            diff = (cur.date - prev_date).days
            for i in range(1, diff):
                yield CurrencyCourse(prev_date + timedelta(days=i),
                                     prev_value)

            yield cur
            mem['cur'] = cur

    return list(walk())


def prepare_currency(cache, rq, start, end):
    key_name = '.{}.pickle'.format(rq)

    cached = cache.get(key_name)
    if cached:
        return cached

    seq = load_currency(rq, start, end)
    seq = fill_gaps(seq)

    cache.set(key_name, seq)

    return seq


def get_currencies_map(cache, cur_map, start, end):
    res = {}

    for name, rq in cur_map.items():
        seq = prepare_currency(cache, rq, start, end)
        res[name] = {d: v for d, v in seq}

    return res
