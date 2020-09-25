"""Peewee models for storing data."""
from __future__ import annotations

import pathlib

from discord.ext import commands

import peewee

import polychess


db_file = pathlib.Path(__file__).parent.parent.absolute() / 'db.sqlite'
db = peewee.SqliteDatabase(db_file)


class BaseModel(peewee.Model):
    """Base model to set Peewee options globally."""

    class Meta:
        """Set Peewee options."""

        legacy_table_names = False
        database = db


class Session(BaseModel):
    """A model to store user sessions."""

    id = peewee.IntegerField(primary_key=True)
    token = peewee.CharField(max_length=128)
    user_id = peewee.BigIntegerField()    # Discord user ID

    @classmethod
    def get_by_ctx(cls, ctx: commands.Context) -> Session:
        """Get an instance of this model from a discord.py context."""
        return cls.get_or_none(cls.user_id == ctx.author.id)

    @classmethod
    def create_from_session(
            cls, session: polychess.Session, user_id: int) -> Session:
        """Create from a polychess session object."""
        return cls.create(id=session.id, token=session.token, user_id=user_id)

    def get_session(self, client: polychess.Client) -> polychess.Session:
        """Get a polychess session object from this instance."""
        return polychess.Session(client, self.token, self.id)


db.create_tables([Session])
