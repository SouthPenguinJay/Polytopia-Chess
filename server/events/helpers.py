"""Helpers for all events, and setting up the server."""
import functools
import json
import typing

import flask

import flask_socketio as sockets

from .. import models
from ..endpoints import converters
from ..endpoints.helpers import RequestError, app


socketio = sockets.SocketIO(app)


class EventContext:
    """Information to be stored during handling of an event."""

    def __init__(
            self, game: models.Game, side: models.Side, user: models.User):
        """Store the initial data."""
        self.game = game
        self.side = side
        self.user = user


def get_context() -> EventContext:
    """Get context for this socket."""
    sid = flask.request.sid
    game = models.Game.get_or_none(models.Game.host_socket_id == sid)
    if game:
        side = models.Side.HOME
        user = game.host
    else:
        game = models.Game.get_or_none(
            models.Game.away_socket_id == sid
        )
        side = models.Side.AWAY
        user = game.away
        if not game:
            raise RequestError(4101)
    return EventContext(game, side, user)


def send_room(name: str, data: typing.Dict[str, typing.Any], room: str):
    """Send an event to a specified room.

    Doesn't do much wrapping of socketio.emit, mainly exists in case we want
    to add more wrapping later.
    """
    socketio.emit(name, data, room=room)


def send_user(name: str, data: typing.Dict[str, typing.Any]):
    """Send an event to the currently connected user."""
    send_room(name, data, flask.request.sid)


def send_game(name: str, data: typing.Dict[str, typing.Any]):
    """Send an event to both members of the currently connected game."""
    send_room(name, data, str(flask.request.context.games.id))


def send_opponent(name: str, data: typing.Dict[str, typing.Any]):
    """Send an event to the opponent of the currently connected user."""
    if flask.request.context.side == models.Side.HOME:
        socket = flask.request.context.game.away_socket_id
    else:
        socket = flask.request.context.game.host_socket_id
    send_room(name, data, socket)


def event(name: str) -> typing.Callable:
    """Create a wrapper for a socket.io event listener."""

    def wrapper(main: typing.Callable) -> typing.Callable:
        """Wrap an endpoint."""
        converter_wrapped = converters.wrap(main)

        @functools.wraps(main)
        def return_wrapped(
                **kwargs: typing.Dict[str, typing.Any]) -> typing.Any:
            """Handle errors and convert the response to JSON."""
            try:
                flask.request.context = get_context()
                converter_wrapped(**kwargs)
            except RequestError as error:
                if name == 'connect':
                    # Don't accept connection if there is an error on connect.
                    raise sockets.ConnectionRefusedError(
                        json.dumps(error.as_dict)
                    )
                else:
                    socketio.emit(
                        'bad_request', error.as_dict, room=flask.request.sid
                    )

        flask_wrapped = socketio.on(name)(return_wrapped)
        return flask_wrapped

    return wrapper
