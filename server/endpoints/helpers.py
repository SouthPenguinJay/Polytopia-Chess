"""Helpers for all endpoints."""
from __future__ import annotations

import base64
import functools
import json
import math
import pathlib
import re
import traceback
import typing

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

import flask

import peewee

from . import converters
from .. import config, models


app = flask.Flask(__name__)


errors_file = pathlib.Path(__file__).parent.absolute() / 'errors.json'

with open(errors_file) as f:
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


def _decrypt_request(raw: bytes) -> typing.Dict[str, typing.Any]:
    """Decrypt a JSON object encrypted with our public key."""
    try:
        raw_json = config.PRIVATE_KEY.decrypt(
            raw,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    except ValueError:
        raise RequestError(3113)
    try:
        return json.loads(raw_json.decode())
    except json.JSONDecodeError:
        raise RequestError(3113)
    except UnicodeDecodeError:
        raise RequestError(3113)


def validate_session_key(
        session_id: typing.Union[int, str],
        session_token: str) -> typing.Optional[models.Session]:
    """Get a session for a session ID and token."""
    if isinstance(session_id, str):
        try:
            session_id = int(session_id)
        except ValueError:
            raise RequestError(1309)
    try:
        session_token = base64.b64decode(session_token)
    except ValueError:
        raise RequestError(3112)
    try:
        session = models.Session.get_by_id(session_id)
    except peewee.DoesNotExist:
        raise RequestError(1304)
    if session_token != bytes(session.token):
        raise RequestError(1305)
    if session.expired:
        session.delete_instance()
        raise RequestError(1306)
    return session


def _process_request(
        request: flask.Request, method: str,
        encrypt_request: bool,
        require_verified_email: bool) -> typing.Dict[str, typing.Any]:
    """Handle authentication and encryption."""
    if method in ('GET', 'DELETE'):
        data = dict(request.args)
    elif method in ('POST', 'PATCH'):
        if encrypt_request:
            data = _decrypt_request(request.get_data())
        else:
            data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            raise RequestError(3113)
    session_id = None
    session_token = None
    if 'session_id' in data:
        session_id = data.pop('session_id')
    if 'session_token' in data:
        session_token = data.pop('session_token')
    if bool(session_id) ^ bool(session_token):
        raise RequestError(1303)
    if session_id and session_token:
        session = validate_session_key(session_id, session_token)
        request.session = session
        user = session.user
        if require_verified_email and not user.email_verified:
            raise RequestError(1307)
        data['user'] = user
    else:
        request.session = None
    return data


def endpoint(
        url: str, method: str,
        encrypt_request: bool = False,
        raw_return: bool = False,
        require_verified_email: bool = False) -> typing.Callable:
    """Create a wrapper for an endpoint."""
    method = method.upper()
    if method not in ('GET', 'DELETE', 'POST', 'PATCH'):
        raise RuntimeError(f'Unhandled method "{method}".')
    if encrypt_request and method not in ('POST', 'PATCH'):
        raise RuntimeError('Cannot encrypt bodyless request.')

    def wrapper(main: typing.Callable) -> typing.Callable:
        """Wrap an endpoint."""
        converter_wrapped = converters.wrap(main)

        @functools.wraps(main)
        def return_wrapped(
                **kwargs: typing.Dict[str, typing.Any]) -> typing.Any:
            """Handle errors and convert the response to JSON."""
            try:
                data = _process_request(
                    flask.request, method, encrypt_request,
                    require_verified_email
                )
                data.update(kwargs)
                response = converter_wrapped(**data)
            except RequestError as error:
                response = error.as_dict
                code = 400
            else:
                code = 200
            if response is None:
                code = 204
            if raw_return:
                response = response or ''
                return flask.Response(
                    response, status=code, mimetype='text/plain'
                )
            else:
                response = flask.jsonify(response or {})
                return response, code

        flask_wrapped = app.route(url, methods=[method])(return_wrapped)
        return flask_wrapped

    return wrapper


@endpoint('/rsa_key', method='GET', raw_return=True)
def get_public_key() -> str:
    """Get our public RSA key."""
    return config.PUBLIC_KEY


@app.errorhandler(404)
def not_found(_error: typing.Any) -> flask.Response:
    """Handle an unkown URL being used."""
    return flask.jsonify(RequestError(3301).as_dict), 404


@app.errorhandler(500)
def internal_error(error: Exception) -> flask.Response:
    """Handle an internal error."""
    traceback.print_tb(error.__traceback__)
    print(f'{type(error).__name__}: {error}')
    return flask.jsonify(RequestError(4001).as_dict), 500
