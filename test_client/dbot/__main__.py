"""The main discord bot."""
import json
import logging
import pathlib

from discord.ext import commands

import polychess

from .cogs import COGS
from .tools.helpcmd import Help


logging.basicConfig(level=logging.INFO)

_config_file = pathlib.Path(__file__).parent.absolute() / 'config.json'
with open(_config_file) as f:
    config = json.load(f)

bot = commands.Bot(command_prefix=config['prefix'], help_command=Help())
bot.client = polychess.Client()
for cog in COGS:
    bot.add_cog(cog(bot))

bot.run(config['token'])
