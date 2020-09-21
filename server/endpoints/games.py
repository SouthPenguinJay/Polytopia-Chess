"""Respond to game related API calls.

This module does not handle encryption, or socket requests, eg. making moves,
sending game invitations, etc.
"""
import datetime
import enum
import typing

import peewee

import models

from .helpers import paginate
from .converters import convert


def dt(x: datetime.datetime) -> int:
    """Utility for converting datetimes to ints."""
    return int(x.timestamp())


def td(x: datetime.timedelta):
    """Utility for converting timedeltas to ints."""
    return int(x.total_seconds())


def _get_list_of_games(
        conditions: typing.Tuple[peewee.Query], page: int,
        *fields: typing.Tuple[str]) -> typing.List[
            typing.Dict[str, typing.Any]]:
    """Get some list of games including given fields."""
    games = []
    query = models.Game.select(
        models.Game, models.HostUser, models.AwayUser
    ).join(
        models.HostUser, join_type=peewee.JOIN.LEFT_OUTER,
        on=(models.Game.host == models.HostUser.id)
    ).join(
        models.AwayUser, join_type=peewee.JOIN.LEFT_OUTER,
        on=(models.Game.away == models.AwayUser.id)
    ).join(
        models.InvitedUser, join_type=peewee.JOIN.LEFT_OUTER,
        on=(models.Game.invited == models.InvitedUser.id)
    ).where(
        *conditions
    )
    query, pages = paginate(query, page)
    users = {}
    for game in query:
        dumped = {
            'id': game.id,
            'mode': game.mode,
            'main_thinking_time': td(game.main_thinking_time),
            'fixed_extra_time': td(game.fixed_extra_time),
            'time_increment_per_turn': td(game.time_increment_per_turn)
        }
        if game.started_at:
            dumped['started_at'] = dt(game.started_at)
        else:
            dumped['opened_at'] = dt(game.opened_at)
        for user_field in ('host', 'away', 'invited'):
            user = getattr(game, user_field)
            if user:
                dumped[user_field] = user.id
                if user.id not in users:
                    users[user.id] = user.to_json()
        for field in fields:
            value = getattr(game, field)
            if isinstance(value, datetime.datetime):
                value = dt(value)
            elif isinstance(value, enum.Enum):
                value = int(value)
            dumped[field] = value
        games.append(dumped)
    return {
        'games': games,
        'users': users,
        'pages': pages
    }


@convert
def get_incoming_invites(
        user: models.User, page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get a list of incoming invites for a user."""
    return _get_list_of_games((models.Game.invited == user,), page)


@convert
def get_outgoing_searches(
        user: models.User, page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get a list of game searches and outgoing invites for a user."""
    return _get_list_of_games(
        (
            models.Game.host == user,
            models.Game.started_at == None    # noqa: E711
        ),
        page
    )


@convert
def get_ongoing_games(
        user: models.User, page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get games a user is currently taking part in."""
    return _get_list_of_games(
        (
            (models.Game.host == user) | (models.Game.away == user),
            models.Game.started_at != None,    # noqa: E711
            models.Game.ended_at == None    # noqa: E711
        ),
        page, 'last_turn'
    )


@convert
def get_completed_games(
        account: models.User, page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get games a user has completed."""
    return _get_list_of_games(
        (
            (models.Game.host == account) | (models.Game.away == account),
            models.Game.ended_at != None    # noqa: E711
        ),
        page, 'ended_at', 'conclusion_type'
    )


@convert
def get_common_completed_games(
        user: models.User, account: models.User,
        page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get games two users have played together."""
    return _get_list_of_games(
        (
            (
                (models.Game.host == user) & (models.Game.away == account)
                | (models.Game.host == account) & (models.Game.away == user)
            ),
            models.Game.ended_at != None    # noqa: E711
        ),
        page, 'ended_at', 'conclusion_type'
    )
