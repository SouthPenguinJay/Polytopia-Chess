"""The main discord bot."""
import json
import logging
import pathlib

from discord.ext import commands

import kasupel

from .cogs import COGS
from .tools.helpcmd import Help


logging.basicConfig(level=logging.INFO)

config_file = pathlib.Path(__file__).parent.absolute() / 'config.json'
with open(config_file) as f:
    config = json.load(f)

bot = commands.Bot(command_prefix=config['prefix'], help_command=Help())
bot.client = kasupel.Client(config['api_url'])
for cog in COGS:
    bot.add_cog(cog(bot))

bot.run(config['token'])
