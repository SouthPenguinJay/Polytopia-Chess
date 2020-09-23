"""Discord.py command checks."""
from discord.ext import commands

from . import models


def authenticated() -> commands.check:
    """Enforce the user being logged in."""

    def predicate(ctx: commands.Context) -> bool:
        """Check the user is logged in."""
        ctx.session_model = models.Session.get_by_ctx(ctx)
        if not ctx.session_model:
            return False
        ctx.session = ctx.session_model.get_session(ctx.bot.client)
        return True

    return commands.check(predicate)
