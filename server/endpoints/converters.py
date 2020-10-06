"""Detect and convert the parameters passed to endpoints."""
import base64
import datetime
import enum
import functools
import inspect
import typing

import peewee

from . import helpers


def int_converter(value: typing.Union[str, int]) -> int:
    """Convert an integer parameter."""
    try:
        return int(value)
    except ValueError:
        raise helpers.RequestError(3111)


def _bytes_converter(value: typing.Union[str, bytes]) -> bytes:
    """Convert a bytes parameter that may have been passed as base64."""
    if isinstance(value, bytes):
        return value
    try:
        return base64.b64decode(str(value))
    except ValueError:
        raise helpers.RequestError(3112)


def _dict_converter(
        value: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
    """Convert a dict (JSON) parameter.

    Does no actual conversion, only validation.
    """
    if not isinstance(value, dict):
        raise helpers.RequestError(3113)
    return value


def _timedelta_converter(value: typing.Union[str, int]) -> datetime.timedelta:
    """Convert a time delta parameter.

    This should be passed as an integer representing seconds.
    """
    value = int_converter(value)
    return datetime.timedelta(seconds=value)


def _make_enum_converter(enum_class: enum.Enum) -> typing.Callable:
    """Create a converter for an enum class."""
    def enum_converter(value: typing.Union[str, int]) -> enum.Enum:
        """Convert a number to the relevant value in an enum."""
        value = int_converter(value)
        try:
            return enum_class(value)
        except ValueError:
            raise helpers.RequestError(3114)
    return enum_converter


def _plain_converter(converter: typing.Callable) -> typing.Callable:
    """Wrap a converter and raise an error if no value is provided."""
    @functools.wraps(converter)
    def main(value: typing.Any) -> typing.Any:
        if value is not None:
            return converter(value)
        raise helpers.RequestError(3101)
    return main


def _default_converter(
        default: typing.Any, converter: typing.Callable) -> typing.Callable:
    """Wrap a converter and provide a default value."""
    @functools.wraps(converter)
    def main(value: typing.Any) -> typing.Any:
        return converter(value) if value else default
    return main


def get_converters(
        endpoint: typing.Callable) -> typing.Tuple[
            bool, typing.Dict[str, typing.Callable]]:
    """Detect the type hints used and provide converters for them."""
    converters = {}
    authenticated = False
    params = inspect.signature(endpoint).parameters.items()
    for n, param in enumerate(params):
        name, details = param
        if n == 0 and name == 'user':
            authenticated = True
            continue
        type_hint = details.annotation
        if isinstance(type_hint, str):
            # If `from __future__ import annotations` is used, annotations
            # will be strings.
            type_hint = eval(endpoint, endpoint.__globals__)
        if type_hint == str:
            converter = str
        elif type_hint == int:
            converter = int_converter
        elif type_hint == bytes:
            converter = _bytes_converter
        elif type_hint == datetime.timedelta:
            converter = _timedelta_converter
        elif issubclass(type_hint, peewee.Model):
            converter = type_hint.converter
        elif issubclass(type_hint, enum.Enum):
            converter = _make_enum_converter(type_hint)
        elif type_hint == typing.Dict:
            converter = _dict_converter
        else:
            raise RuntimeError(f'Converter needed for argument {name}.')
        if details.default != inspect._empty:
            converter = _default_converter(details.default, converter)
        else:
            converter = _plain_converter(converter)
        converters[name] = converter
    return authenticated, converters


def wrap(endpoint: typing.Callable) -> typing.Callable:
    """Wrap an endpoint to convert its arguments."""
    authenticated, converters = get_converters(endpoint)

    @functools.wraps(endpoint)
    def wrapped(**kwargs: typing.Dict[str, typing.Any]) -> typing.Any:
        """Convert arguments before calling the endpoint."""
        if authenticated and not kwargs.get('user'):
            raise helpers.RequestError(1301)
        elif kwargs.get('user') and not authenticated:
            del kwargs['user']
        converted = {}
        for kwarg in kwargs:
            if kwarg in converters:
                converted[kwarg] = converters[kwarg](kwargs[kwarg])
            else:
                converted[kwarg] = kwargs[kwarg]
        try:
            return endpoint(**converted)
        except TypeError:
            # Unexpected key word argument or missing required argument.
            raise helpers.RequestError(3102)

    return wrapped
