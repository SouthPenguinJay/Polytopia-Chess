"""Display paginated responses from the API in Discord."""
import typing

import discord
from discord.ext import commands

import kasupel


class Paginator:
    """A class to display paginated data."""

    def __init__(
            self, ctx: commands.Context, response: kasupel.Paginator,
            fmt: typing.Callable, title: str):
        """Set up the paginator."""
        self.ctx = ctx
        self.response = response
        self.format = fmt
        self.title = title
        self.message = None
        ctx.bot.add_listener(self.on_reaction_add)

    async def display_page(self):
        """Display the current page."""
        lines = []
        for n, item in zip(range(self.response.per_page), self.response):
            lines.append(self.format(n=n + 1, item=item))
        desc = '\n'.join(lines) or '*There\'s nothing here.*'
        e = discord.Embed(title=self.title, description=desc)
        e.set_footer(
            text=f'Page {self.response.page_number + 1}/{self.response.pages}'
        )
        if self.message:
            await self.message.edit(embed=e)
        else:
            self.message = await self.ctx.send(embed=e)
            if self.response.pages > 1:
                await self.message.add_reaction('◀')
                await self.message.add_reaction('▶')

    async def back(self):
        """Go to the previous page."""
        if self.response.page_number > 0:
            self.response.page_number -= 1
            await self.display_page()

    async def forward(self):
        """Go to the next page."""
        if self.response.page_number + 1 < self.response.pages:
            self.response.page_number += 1
            await self.display_page()

    async def on_reaction_add(
            self, reaction: discord.Reaction, user: discord.User):
        """Process a reaction being added."""
        if user != self.ctx.author:
            return
        if reaction.message.id != self.message.id:
            return
        if reaction.emoji == '▶':
            await self.forward()
        elif reaction.emoji == '◀':
            await self.back()
        await reaction.remove(user)
