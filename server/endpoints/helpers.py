"""Helpers for all endpoints."""
import enum
import json
import math
import re
import typing

import peewee


with open('endpoints/errors.json') as f:
    ERROR_CODES = json.load(f)


class RequestError(Exception):
    """A class for errors caused by a bad request."""

    def __init__(self, code: int):
        """Store the code and message to be handled."""
        self.code = code
        self.message = ERROR_CODES[str(code)]
        super().__init__(self.message)


def paginate(
        query: peewee.SelectQuery, page: int = 0,
        per_page: int = 100) -> typing.Tuple[peewee.SelectQuery, int]:
    """Paginate the results of a query.

    Returns results and number of pages.
    """
    total_results = query.count()
    pages = math.ceil(total_results / per_page)
    if pages and page >= pages:
        raise RequestError(3201)
    page = query.offset(page * per_page).limit(per_page)
    return page, pages


def interpret_integrity_error(error: peewee.IntegrityError):
    """Dissect an integrity error to see what went wrong.

    It seems like a bad way to do it but according to peewee's author it's
    the only way: https://stackoverflow.com/a/53597548.
    """
    match = re.search(
        r'DETAIL:  Key \(([a-z_]+)\)=\((.+)\) already exists\.', str(error)
    )
    if match:
        return 'duplicate', match.group(1)
    else:
        raise ValueError('Unknown integrity error.') from error
