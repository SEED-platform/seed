"""
:copyright: (c) 2014 Building Energy Inc
"""
import json
from dateutil import parser
from itertools import islice, chain


def batch(iterable, size):
    """Generator to return iterators of size ``size``.

    :param iterable: any iterable type, items you need batched up.
    :param size: int, batch size.
    :rtype: iterable or lists.

    """
    sourceiter = iter(iterable)
    while 1:
        batchiter = islice(sourceiter, size)
        yield list(chain([batchiter.next()], batchiter))


def date_str_to_date(date_str):
    if date_str:
        return parser.parse(date_str)


def load_ontology(filename):
    """Load json structure from a file."""
    with open(filename, 'rb') as f:
        return json.loads(f.read())
