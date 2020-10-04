"""The meta cog."""
import discord
from discord.ext import commands

from ..tools.errors import on_command_error


ABOUT = (
    'This bot was made by Artemis#9784. Its sole purpose is to implement the '
    'Kasupel API, mainly for testing purposes.'
)


class Meta(commands.Cog):
    """Commands relating to the bot itself."""

    def __init__(self, bot: commands.Bot):
        """Store a reference to the bot."""
        self.bot = bot
        bot.help_command.cog = self

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Send prefix if bot is mentioned."""
        if message.guild:
            me = message.guild.me
        else:
            me = self.bot.user
        if me in message.mentions:
            await message.channel.send(
                f'My prefix is `{self.bot.command_prefix}`.'
            )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Handle an error."""
        await on_command_error(ctx, error)

    @commands.command(brief='About the bot.')
    async def about(self, ctx: commands.Context):
        """Get some information about the bot."""
        embed = discord.Embed(
            title='About',
            description=ABOUT,
            colour=0x45b3e0
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        await ctx.send(embed=embed)
