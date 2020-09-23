"""Discord.py command checks."""
from discord.ext import commands


def authenticated() -> commands.check:
    """Enforce the user being logged in."""

    def predicate(ctx: commands.Context) -> bool:
        """Check the user is logged in."""
        if ctx.author.id in ctx.bot.sessions:
            ctx.session = ctx.bot.sessions[ctx.author.id]
            return True
        else:
            return False

    return commands.check(predicate)
