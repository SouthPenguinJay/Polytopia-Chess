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


def _get_list_of_games(
        query: peewee.SelectQuery, page: int,
        *fields: typing.Tuple[str]) -> typing.List[
            typing.Dict[str, typing.Any]]:
    """Get some list of games including given fields."""
    games = []
    query, pages = paginate(query, page)
    for game in query:
        dumped = {
            'id': game.id,
            'mode': game.mode,
            'main_thinking_time': game.main_thinking_time,
            'fixed_extra_time': game.fixed_extra_time,
            'time_increment_per_turn': game.time_increment_per_turn
        }
        if game.started_at:
            dumped['started_at'] = game.started_at.to_timestamp()
        else:
            dumped['opened_at'] = game.opened_at.to_timestamp()
        for field in fields:
            value = getattr(game, field)
            if isinstance(value, models.User):
                value = value.to_json()
            elif isinstance(value, datetime.datetime):
                value = value.to_timestamp()
            elif isinstance(value, enum.Enum):
                value = int(value)
            dumped[field] = value
        games.append(dumped)
    return {
        'games': games,
        'pages': pages
    }


def get_incoming_invites(
        user: models.User, page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get a list of incoming invites for a user."""
    return _get_list_of_games(user.invites, 'host')


def get_outgoing_searches(
        user: models.User, page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get a list of game searches and outgoing invites for a user."""
    return _get_list_of_games(
        user.games.where(
            models.Game.host == user,
            models.Game.started_at == None    # noqa: E711
        ),
        'invited'
    )


def get_ongoing_games(
        user: models.User, page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get games a user is currently taking part in."""
    return _get_list_of_games(
        user.games.where(
            models.Game.started_at != None,    # noqa: E711
            models.Game.ended_at == None    # noqa: E711
        ),
        'last_turn'
    )


def get_completed_games(
        user: models.User, page: int = 0) -> typing.Dict[str, typing.Any]:
    """Get games a user has completed."""
    return _get_list_of_games(
        user.games.where(models.Game.ended_at != None),    # noqa: E711
        'ended_at', 'conclusion_type'
    )
