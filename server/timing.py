"""Utilities for controlling the timers."""
from __future__ import annotations

import datetime

from . import models


class Timer:
    """A timer for a game.

    It retains no state other than a references to a game in the database.
    Therefore, each time it is needed, a new instance can be created or an
    existing one can be used - it makes no difference.
    """

    def __init__(self, game: models.Game):
        """Store the game we are interested in."""
        self.game = game

    def turn_end(self, side: models.Side):
        """Increment timers for the end of a turn."""
        last_turn = self.game.last_turn
        current_time = datetime.datetime.now()
        turn_length = current_time - last_turn
        if turn_length > self.game.fixed_extra_time:
            main_time_used = turn_length - self.game.fixed_extra_time
        else:
            main_time_used = datetime.timedelta(0)
        timer_delta = self.game.time_increment_per_turn - main_time_used
        if side == models.Side.HOME:
            self.game.home_time += timer_delta
        else:
            self.game.away_time += timer_delta
        self.game.last_turn = current_time

    @property
    def boundary(self) -> datetime.datetime:
        """Return the time the current player will run out of time."""
        current_timer = (
            self.game.home_time
            if self.game.current_turn == models.Side.HOME
            else self.game.away_time
        )
        return (
            self.game.last_turn
            + current_timer
            + self.game.fixed_extra_time
        )


# TODO: Actually use timing.
