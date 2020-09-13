"""A collection of the game modes (currently only chess)."""
from __future__ import annotations

import typing

import models


class GameMode:
    """A base class for games, not intended to be used itself."""

    def __init__(self, game: models.Game):
        """Store the game we are interested in."""
        self.game = game

    def layout_board(self):
        """Put the pieces on the board."""
        raise NotImplementedError

    def validate_move(
            self, start_rank: int, start_file: int, end_rank: int,
            end_file: int) -> bool:
        """Validate a move."""
        raise NotImplementedError

    def possible_moves(self, side: models.Side) -> typing.Iterator[
            typing.Tuple[models.Piece, int, int]]:
        """Get all possible moves for a side."""
        raise NotImplementedError

    def game_is_over(self) -> models.Conclusion:
        """Check if the game has been won or tied.

        If the return value is checkmate, the player whos turn it currently
        is is in checkmate. This method must be called after the GameState
        for the current turn has been created.
        """
        raise NotImplementedError

    def freeze_game(self) -> str:
        """Store a snapshot of a game as a string."""
        raise NotImplementedError
