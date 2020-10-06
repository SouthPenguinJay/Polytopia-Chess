"""Discord.py command error handler."""
import re
import traceback

import discord
from discord.ext.commands import CommandNotFound, Context

from kasupel import RequestError


async def on_command_error(ctx: Context, error: Exception):
    """Handle an error."""
    if isinstance(error, CommandNotFound):
        return
    if hasattr(error, 'original'):
        err = error.original
        if isinstance(err, RequestError):
            e = discord.Embed(
                colour=0xe94b3c, title='API Error', description=err.message
            )
            await ctx.send(embed=e)
            return
        traceback.print_tb(err.__traceback__)
        print(f'{type(err).__name__}: {err}.')
    rawtitle = type(error).__name__
    rawtitle = re.sub('([a-z])([A-Z])', r'\1 \2', rawtitle)
    title = rawtitle[0].upper() + rawtitle[1:].lower()
    e = discord.Embed(
        colour=0xe94b3c, title=title, description=str(error)
    )
    await ctx.send(embed=e)
