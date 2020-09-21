"""Helpers for all endpoints."""
from __future__ import annotations

import json
import functools
import math
import re
import typing

import flask

import peewee

import models

from . import converters


app = flask.Flask(__name__)


with open('endpoints/errors.json') as f:
    ERROR_CODES = json.load(f)


class RequestError(Exception):
    """A class for errors caused by a bad request."""

    def __init__(self, code: int):
        """Store the code and message to be handled."""
        self.code = code
        self.message = ERROR_CODES[str(code)]
        self.as_dict = {
            'error': code,
            'message': self.message
        }
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


def interpret_integrity_error(
        error: peewee.IntegrityError) -> typing.Tuple[str, str]:
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


def _process_request(
        request: flask.Request, encrypt_request: bool) -> typing.Tuple[
            models.User, typing.Dict[str, typing.Any]]:
    """Handle authentication and encryption."""
    # TODO: Implement.
    return None, {}


def endpoint(
        url: str, method: str,
        encrypt_request: bool = False) -> typing.Callable:
    """Create a wrapper for an endpoint."""

    def wrapper(endpoint: typing.Callable) -> typing.Callable:
        """Wrap an endpoint."""
        converter_wrapped = converters.wrap(endpoint)

        @functools.wraps(endpoint)
        def return_wrapped(
                **kwargs: typing.Dict[str, typing.Any]) -> typing.Any:
            """Handle errors and convert the response to JSON."""
            user, data = _process_request(flask.request, encrypt_request)
            data.update(kwargs)
            if user:
                data['user'] = user
            try:
                response = converter_wrapped(**data) or {}
            except RequestError as error:
                response = error.as_dict
                code = 400
            else:
                code = 200
            response = flask.jsonify(response)
            response.status_code = code
            return response

        flask_wrapped = app.route(url, methods=[method])(return_wrapped)
        return flask_wrapped

    return wrapper
