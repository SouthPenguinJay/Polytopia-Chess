"""A cog to manage user accounts."""
import discord
from discord.ext import commands

from ..tools import models
from ..tools.checks import authenticated
from ..tools.paginator import Paginator


Ctx = commands.Context


class Accounts(commands.Cog):
    """A cog to manage user accounts."""

    def __init__(self, bot: commands.Bot):
        """Store a reference to the bot."""
        self.bot = bot

    @commands.command(brief='Log in to your account.')
    @commands.dm_only()
    async def login(self, ctx: Ctx, username: str, *, password: str):
        """Login with your username and password.

        This must be run in DMs.
        """
        if models.Session.get_by_ctx(ctx):
            await ctx.send('You are already logged in.')
            return
        session = self.bot.client.login(username, password)
        models.Session.create_from_session(session, ctx.author.id)
        await ctx.send('Successful login.')

    @commands.command(brief='Log out of your account.')
    @authenticated()
    async def logout(self, ctx: Ctx):
        """Logout of your account."""
        ctx.session.logout()
        ctx.session_model.delete_instance()
        await ctx.send('Successful logout.')

    @commands.command(
        brief='Resend verification email.', name='resend-verification'
    )
    @authenticated()
    async def resend_verification(self, ctx: Ctx):
        """Resend your verification email."""
        ctx.session.resend_verification_email()
        await ctx.send('Email resent.')

    @commands.command(brief='Change your password.', name='change-password')
    @commands.dm_only()
    @authenticated()
    async def change_password(self, ctx: Ctx, *, password: str):
        """Change your password."""
        ctx.session.update(password=password)
        ctx.session_model.delete_instance()
        new_session = self.bot.client.login(
            ctx.user.username, password
        )
        models.Session.create_from_session(new_session, ctx.author.id)
        await ctx.send('Changed password and logged in again.')

    @commands.command(brief='Change your email address.', name='change-email')
    @commands.dm_only()
    @authenticated()
    async def change_email(self, ctx: Ctx, *, email: str):
        """Change your email address."""
        ctx.session.update(email=email)
        await ctx.send('Changed email address.')

    @commands.command(brief='Delete your account.', name='delete-account')
    @authenticated()
    async def delete_account(self, ctx: Ctx):
        """Delete your account.

        This is permanent and cannot be undone.
        """
        await ctx.send(
            'Are you sure you want to delete your account? '
            'This is irreversible. `Yes` to continue, anything else to '
            'cancel.'
        )
        response = await self.bot.wait_for(
            'message',
            check=lambda m: (
                m.channel == ctx.channel and m.author == ctx.author
            )
        )
        if 'yes'.startswith(response.content.lower()):
            ctx.session.delete()
            ctx.session_model.delete_instance()
            await ctx.send('Deleted your account.')
        else:
            await ctx.send('Cancelled.')

    @commands.command(brief='View a user\'s details.')
    async def user(self, ctx: Ctx, *, username: str = None):
        """Get a user by their username.

        If you don't give a username, it will return your account.
        If you don't give a username in DMs, it will also show your email.

        Examples:
        `{{pre}}user Artemis`
        `{{pre}}user`
        """
        if username:
            user = self.bot.client.get_user(username=username)
        else:
            session_model = models.Session.get_by_ctx(ctx)
            if not session_model:
                await ctx.send(
                    'You are not logged in, please specify a user.'
                )
                return
            user = session_model.get_session(ctx.bot.client).fetch_user()
        e = discord.Embed(title=user.username, timestamp=user.created_at)
        e.add_field(name='ELO', value=user.elo)
        e.add_field(name='ID', value=user.id)
        e.set_footer(text='Created at')
        is_dm = ctx.channel.type == discord.ChannelType.private
        if user.authenticated and is_dm:
            e.add_field(name='Email', value=user.email)
        await ctx.send(embed=e)

    @commands.command(brief='Create an account.')
    @commands.dm_only()
    async def signup(
            self, ctx: Ctx, username: str, password: str, email: str):
        """Create an account.

        This must be run in DMs.
        Example: `{{pre}}signup Artemis very-bad-password email@example.com`
        """
        self.bot.client.create_account(username, password, email)
        await ctx.send('Successfully created account.')

    @commands.command(brief='Verify email address.', name='verify-email')
    async def verify_email(self, ctx: Ctx, username: str, token: str):
        """Verify your email address, using the token you were emailed.

        Example: `{{pre}}verify-email Artemis INA43K`
        """
        self.bot.client.verify_email(username, token)
        await ctx.send('Email address verified.')

    @commands.command(brief='See the leaderboard.', aliases=['lb'])
    async def leaderboard(self, ctx: Ctx, page: int = 1):
        """View the leaderboard.

        Examplew:
        `{{pre}}leaderboard`
        `{{pre}}lb 5`
        """
        users = self.bot.client.get_users(page - 1)
        await Paginator(
            ctx, users, '`#{n:>3}` {item.username} - {item.elo}'.format,
            'Leaderboard'
        ).display_page()
