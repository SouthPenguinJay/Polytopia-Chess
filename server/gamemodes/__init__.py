"""Collate the gamemodes."""
from . import chess
from .gamemode import GameMode    # noqa: F401


GAMEMODES = [chess.Chess]
