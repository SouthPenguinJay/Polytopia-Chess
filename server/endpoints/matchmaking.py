"""Respond to and send socket API calls related to matchmaking."""
import datetime

import peewee

from .helpers import RequestError, endpoint
from .. import models


# TODO: Implement sockets.
_start_socket_session = lambda x, y: None    # noqa: E731
_end_socket_session = lambda x, y: None      # noqa: E731


# FIXME: Once sockets are implemented, the following three methods should be
#        CONNECT rather than GET.

@models.db.atomic()
@endpoint('/games/find', method='GET', require_verified_email=True)
def find_game(
        user: models.User,
        main_thinking_time: datetime.timedelta,
        fixed_extra_time: datetime.timedelta,
        time_increment_per_turn: datetime.timedelta, mode: int):
    """Find a game matching parameters, or create one if not found."""
    try:
        game = models.Game.get(
            models.Game.host != user,
            models.Game.started_at == None,    # noqa: E7111
            models.Game.main_thinking_time == main_thinking_time,
            models.Game.fixed_extra_time == fixed_extra_time,
            models.Game.time_increment_per_turn == time_increment_per_turn,
            models.Game.mode == mode
        )
    except peewee.DoesNotExist:
        game = models.Game.create(
            host=user, mode=mode, main_thinking_time=main_thinking_time,
            fixed_extra_time=fixed_extra_time,
            time_increment_per_turn=time_increment_per_turn
        )
    else:
        game.start_game(user)
        _start_socket_session(game.host, game)
    _start_socket_session(user, game)


@models.db.atomic()
@endpoint('/games/send_invitation', method='GET', require_verified_email=True)
def send_invitation(
        user: models.User,
        invitee: models.User,
        main_thinking_time: datetime.timedelta,
        fixed_extra_time: datetime.timedelta,
        time_increment_per_turn: datetime.timedelta, mode: int):
    """Create a game which only a specific person may join."""
    if user == invitee:
        raise RequestError(2121)
    game = models.Game.create(
        host=user, invited=invitee, mode=mode,
        main_thinking_time=main_thinking_time,
        fixed_extra_time=fixed_extra_time,
        time_increment_per_turn=time_increment_per_turn
    )
    _start_socket_session(user, game)


@models.db.atomic()
@endpoint('/games/invites/<game>', method='GET', require_verified_email=True)
def accept_invitation(user: models.User, game: models.Game):
    """Accept a game you have been invited to."""
    if game.invited != user:
        raise RequestError(2111)
    game.start_game(user)
    _start_socket_session(user, game)


@models.db.atomic()
@endpoint('/games/invites/<game>', method='DELETE')
def decline_invitation(user: models.User, game: models.Game):
    """Decline a game you have been invited to."""
    if game.invited != user:
        raise RequestError(2111)
    _end_socket_session(game.host, game)
    game.delete_instance()
