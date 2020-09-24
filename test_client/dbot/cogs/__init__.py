"""Collate the cogs."""
from .accounts import Accounts
from .games import Games
from .meta import Meta


COGS = [Accounts, Games, Meta]
