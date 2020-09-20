"""Detect and convert the parameters passed to endpoints."""
import base64
import datetime
import functools
import inspect
import typing

import peewee

from .helpers import RequestError


def _int_converter(value: typing.Union[str, int]) -> int:
    """Convert an integer parameter."""
    try:
        return int(value)
    except ValueError:
        raise RequestError(3101)


def _bytes_converter(value: typing.Union[str, bytes]) -> bytes:
    """Convert a bytes parameter that may have been passed as base64."""
    if isinstance(value, bytes):
        return value
    elif isinstance(value, str):
        try:
            return base64.b64decode(value)
        except ValueError:
            raise RequestError(3102)


def _timedelta_converter(value: typing.Union[str, int]) -> datetime.timedelta:
    """Convert a time delta parameter.

    This should be passed as an integer representing seconds.
    """
    value = _int_converter(value)
    return datetime.timedelta(seconds=value)


def _plain_converter(converter: typing.Callable) -> typing.Callable:
    """Wrap a converter and raise an error if no value is provided."""
    @functools.wraps(converter)
    def main(value: typing.Any) -> typing.Any:
        if value is not None:
            return converter(value)
        raise RequestError(3001)
    return main


def _default_converter(
        default: typing.Any, converter: typing.Callable) -> typing.Callable:
    """Wrap a converter and provide a default value."""
    @functools.wraps(converter)
    def main(value: typing.Any) -> typing.Any:
        return converter(value) if value else default
    return main


def get_converters(
        endpoint: typing.Callable) -> typing.Dict[str, typing.Callable]:
    """Detect the type hints used and provide converters for them."""
    converters = {}
    params = inspect.signature(endpoint).parameters.items()
    for n, param in enumerate(params):
        name, details = param
        if n == 0 and name == 'user':
            continue
        type_hint = details.annotation
        if isinstance(type_hint, str):
            # If `from __future__ import annotations` is used, annotations
            # will be strings.
            type_hint = eval(endpoint, endpoint.__globals__)
        if type_hint == str:
            converter = str
        elif type_hint == int:
            converter = _int_converter
        elif type_hint == bytes:
            converter = _bytes_converter
        elif type_hint == datetime.timedelta:
            converter = _timedelta_converter
        elif issubclass(type_hint, peewee.Model):
            converter = type_hint.converter
        else:
            raise RuntimeError(f'Converter needed for argument {name}.')
        if details.default != inspect._empty:
            converter = _default_converter(details.default, converter)
        else:
            converter = _plain_converter(converter)
        converters[name] = converter
    return converters


def convert(endpoint: typing.Callable) -> typing.Callable:
    """Wrap an endpoint to convert its arguments."""
    converters = get_converters(endpoint)

    @functools.wraps(endpoint)
    def wrapper(**kwargs: typing.Dict[str, typing.Any]) -> typing.Any:
        """Convert arguments before calling the endpoint."""
        converted = {}
        for kwarg in kwargs:
            if kwarg in converters:
                converted[kwarg] = converters[kwarg](kwargs[kwarg])
            else:
                converted[kwarg] = kwargs[kwarg]
        return endpoint(**converted)

    return wrapper
