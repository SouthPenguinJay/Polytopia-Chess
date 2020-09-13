"""Helpers for all endpoints."""
import json
import math
import typing

import peewee


with open('endpoints/errors.json') as f:
    ERROR_CODES = json.load(f)


class RequestError(Exception):
    """A class for errors caused by a bad request."""

    def __init__(self, code: int):
        """Store the code and message to be handled."""
        self.code = code
        self.message = ERROR_CODES[code]
        super().__init__(self.message)


def paginate(
        query: peewee.SelectQuery, page: int = 0,
        per_page: int = 100) -> typing.Tuple[peewee.SelectQuery, int]:
    """Paginate the results of a query.

    Returns results and number of pages.
    """
    total_results = query.count()
    pages = math.ceil(total_results / per_page)
    page = query.offset(page * per_page).limit(per_page)
    return page, pages
