import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sqlite3
import sys
import os
import glob
import typing
from .lib import utils
from .lib import settings
from .lib import sqlite
from .lib import mongo
from .lib import logger
from .lib import loglevel
from .lib import dbprovider
class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "events.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "events.__init__", f"SQLITE DB Path: {self.settings.db_path}")
        self.log.debug(0, "events.__init__", f"Logger initialized with level {log_level.name}")



    @commands.Cog.listener()
    async def on_ready(self):
        self.log.debug(0, "events.on_ready", f"Logged in as {self.bot.user.name}:{self.bot.user.id}")
        self.log.debug(0, "events.on_ready", f"Setting Bot Presence '🔊 Creating Voice Channels Like A Boss 🔊'")
        await self.bot.change_presence(activity=discord.Game(name="🔊 Creating Voice Channels Like A Boss 🔊"))

    @commands.Cog.listener()
    async def on_disconnect(self):
        self.log.debug(0, "events.on_disconnect", f"Bot Disconnected")

    @commands.Cog.listener()
    async def on_resumed(self):
        self.log.debug(0, "events.on_resumed", f"Bot Session Resumed")

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        self.log.error(0, "events.on_error", f"{str(event)}", traceback.format_exc())

def setup(bot):
    bot.add_cog(Events(bot))
