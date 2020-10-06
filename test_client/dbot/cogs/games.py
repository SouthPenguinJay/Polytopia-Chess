"""Commands to get lists of games."""
import datetime

import discord
from discord.ext import commands

import kasupel

from ..tools import models
from ..tools.checks import authenticated
from ..tools.paginator import Paginator


Ctx = commands.Context


def pretty_td(td: datetime.timedelta) -> str:
    """Format a timdelta to display."""
    hours, seconds = divmod(td.seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    weeks, days = divmod(td.days, 7)
    display = ''
    parts = {
        'w': weeks,
        'd': days,
        'h': hours,
        'm': minutes,
        's': seconds
    }
    display = ''.join(str(parts[i]) + i for i in parts if parts[i])
    return display or '0s'


def parse_td(raw: str) -> datetime.timedelta:
    """Parse a string to a timedelta."""
    lengths = {
        'w': 60 * 60 * 24 * 7,
        'd': 60 * 60 * 24,
        'h': 60 * 60,
        'm': 60,
        's': 1
    }
    parts = []
    part = ''
    for i in raw:
        part += i
        if i in lengths:
            parts.append(part)
            part = ''
    seconds = 0
    for part in parts:
        try:
            value = int(part[:-1])
        except ValueError:
            pass    # FIXME
        seconds += lengths[part[-1]] * value
    return datetime.timedelta(seconds=seconds)


def parse_gamemode(raw: str) -> kasupel.Gamemode:
    """Parse a gamemode."""
    for gamemode in kasupel.Gamemode:
        if gamemode.name.lower() == raw.lower():
            return gamemode
    # FIXME


def format_completed_game(_n: int, item: kasupel.Game) -> str:
    """Format a game that has ended to display it."""
    mode = item.mode.name.title()
    home = item.host.username
    away = item.away.username
    conclusion = {
        kasupel.Winner.HOME: f'{home} won',
        kasupel.Winner.AWAY: f'{away} won',
        kasupel.Winner.DRAW: 'draw'
    }[item.winner]
    return f'({item.id}) {mode} - {home} vs {away}, {conclusion}'


def format_open_game(_n: int, item: kasupel.Game) -> str:
    """Format a game that is open to display it."""
    mode = item.mode.name.title()
    timings = (
        f'{pretty_td(item.main_thinking_time)}+'
        f'{pretty_td(item.time_increment_per_turn)} '
        f'main with {pretty_td(item.fixed_extra_time)} per turn'
    )
    display = f'({item.id}) {mode}, {timings}'
    if item.invited:
        home = item.host.username
        invitee = item.invited.username
        display += f' {home} invited {invitee}'
    return display


def format_ongoing_game(_n: int, item: kasupel.Game) -> str:
    """Format a game that is in progress to display it."""
    mode = item.mode.name.title()
    home = item.host.username
    away = item.away.username
    turn = f'move {item.turn_number}, {item.current_turn.name.lower()} turn'
    return f'({item.id}) {mode} - {home} vs {away}, {turn}'


class Games(commands.Cog):
    """Commands to get lists of games."""

    def __init__(self, bot: commands.Bot):
        """Store a reference to the bot."""
        self.bot = bot

    @commands.command(
        brief='Get someone\'s completed games.', name='completed-games',
        aliases=['completed']
    )
    async def completed_games(self, ctx: Ctx, username: str = None):
        """Get someone's completed games.

        If you pass no arguments (and you're logged in), returns your own
        completed games.
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
            user = session_model.get_session(ctx.bot.client).user
        games = user.get_completed_games()
        await Paginator(
            ctx, games, format_completed_game,
            f'{username}\'s Completed Games'
        )

    @commands.command(
        brief='Get games you have played with someone.',
        name='common-completed-games',
        aliases=['common', 'common-completed', 'common-games']
    )
    @authenticated()
    async def common_completed_games(self, ctx: Ctx, username: str = None):
        """Get games you have completed with someone else."""
        other = self.bot.client.get_user(username=username)
        games = ctx.session.get_common_completed_games(other)
        await Paginator(
            ctx, games, format_completed_game,
            f'{username} and {ctx.session.user.username}\'s Completed Games'
        ).display_page()

    @commands.command(
        brief='Get your invitations.', name='game-invitations',
        aliases=['invitations', 'invites', 'game-invites']
    )
    @authenticated()
    async def game_invitations(self, ctx: Ctx):
        """Get games you have been invited to."""
        games = ctx.session.get_invites()
        await Paginator(
            ctx, games, format_open_game,
            f'{ctx.session.user.username}\'s Invitations'
        ).display_page()

    @commands.command(
        brief='Get outgoing searches.', name='game-searches',
        aliases=['searches']
    )
    @authenticated()
    async def game_searches(self, ctx: Ctx):
        """Get games where you are looking for opponents.

        Also includes games you have invited others to.
        """
        games = ctx.session.get_searches()
        await Paginator(
            ctx, games, format_open_game,
            f'{ctx.session.user.username}\'s Open Games'
        ).display_page()

    @commands.command(
        brief='Get ongoing games.', name='ongoing-games', aliases=['ongoing']
    )
    @authenticated()
    async def ongoing_games(self, ctx: Ctx):
        """Get games which you are currently playing."""
        games = ctx.session.get_ongoing()
        await Paginator(
            ctx, games, format_ongoing_game,
            f'{ctx.session.user.username}\'s Ongoing Games'
        ).display_page()

    @commands.command(brief='Get a game.')
    async def game(self, ctx: Ctx, game_id: int):
        """Get a game by its ID."""
        game = self.bot.client.get_game(game_id)
        home = game.host.username if game.host else '[Deleted User]'
        if game.started_at:
            away = game.away.username if game.away else '[Deleted User]'
        else:
            away = '[Waiting for Opponent]'
        timings = (
            f'Each player starts with {pretty_td(game.main_thinking_time)}. '
            f'Every turn, they have {pretty_td(game.fixed_extra_time)} to '
            'make a move. If they make a move in that time, their timer is '
            'not changed. If they are still thinking after that time, their '
            'timer starts going down. At the end of their turn, they get an '
            f'extra {pretty_td(game.time_increment_per_turn)}.'
        )
        e = discord.Embed(title=f'{home} vs {away}', description=timings)
        e.add_field(name='Gamemode', value=game.mode.name.title())
        if game.invited:
            e.add_field(name='Invited', value=game.invited.username)
        if game.started_at and not game.ended_at:
            to_move = game.current_turn.name.lower()
            e.add_field(
                name='Current Turn',
                value=f'Turn {game.turn_number}, {to_move} to move.'
            )
            home_clock = pretty_td(game.home_time)
            away_clock = pretty_td(game.away_time)
            e.add_field(
                name='Clocks', value=f'Home {home_clock} | {away_clock} Away'
            )
            if game.home_offering_draw:
                e.add_field(name='Offering Draw', value='Home')
            elif game.away_offering_draw:
                e.add_field(name='Offering Draw', value='Away')
            e.add_field(
                name='Last Turn',
                value=game.last_turn.strftime('%d/%m/%y %H:%M')
            )
        e.add_field(
            name='Opened', value=game.opened_at.strftime('%d/%m/%y %H:%M')
        )
        if game.started_at:
            e.add_field(
                name='Started',
                value=game.started_at.strftime('%d/%m/%y %H:%M')
            )
        if game.ended_at:
            e.add_field(
                name='Ended', value=game.ended_at.strftime('%d/%m/%y %H:%M')
            )
            winner = game.winner.name.title()
            conclusion = game.conclusion_type.replace('_', ' ').lower()
            e.add_field(name='Winner', value=f'{winner} by {conclusion}')
        e.set_footer(text=f'ID: {game.id}')
        await ctx.send(embed=e)

    @commands.command(
        brief='Send an invite.', name='send-invitation',
        aliases=['send-invite', 'invite']
    )
    @authenticated()
    async def send_invitation(
            self, ctx: Ctx, invitee: str, mode: parse_gamemode,
            main_thinking_time: parse_td,
            fixed_extra_time: parse_td, time_increment_per_turn: parse_td):
        """Send someone an invitation to a game.

        Example: `{{pre}}invite Artemis chess 1h 0 30s`
        """
        invitee = self.bot.client.get_user(username=invitee)
        ctx.session.send_invitation(
            invitee, main_thinking_time, fixed_extra_time,
            time_increment_per_turn, mode
        )
        await ctx.send('Invitation sent.')

    @commands.command(
        brief='Find a game.', name='search-for-game', aliases=['search']
    )
    @authenticated()
    async def search_for_game(
            self, ctx: Ctx, mode: parse_gamemode,
            main_thinking_time: parse_td,
            fixed_extra_time: parse_td, time_increment_per_turn: parse_td):
        """Search for a game to join, or create one if not found.

        Example: `{{pre}}search chess 10m 30s 0`
        """
        ctx.session.find_game(
            main_thinking_time, fixed_extra_time, time_increment_per_turn,
            mode
        )
        await ctx.send('Started looking...')

    @commands.command(
        brief='Accept an invite.', name='accept-invite', aliases=['accept']
    )
    @authenticated()
    async def accept_invite(self, ctx: Ctx, game_id: int):
        """Join a game you have been invited to."""
        game = ctx.bot.client.get_game(game_id)
        ctx.session.accept_inivitation(game)
        await ctx.send('Accepted invitation.')

    @commands.command(
        brief='Decline an invite.', name='decline-invite', aliases=['decline']
    )
    @authenticated()
    async def decline_invite(self, ctx: Ctx, game_id: int):
        """Reject a game you have been invited to."""
        game = self.bot.client.get_game(game_id)
        ctx.session.decline_inivitation(game)
        await ctx.send('Declined invitation.')
