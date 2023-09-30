import traceback
import inspect
import os

import discord
from bot.cogs.lib import logger, settings, loglevel
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.bot = bot
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(
            0, f"{self._module}.{self._class}.{_method}", f"Initialized with log level {log_level.name}"
        )



    @commands.Cog.listener()
    async def on_ready(self):
        _method = inspect.stack()[0][3]
        self.log.debug(
            0,
            f"{self._module}.{self._class}.{_method}",
            f"Logged in as {self.bot.user.name}:{self.bot.user.id}",
        )
        self.log.debug(
            0,
            f"{self._module}.{self._class}.{_method}",
            f"Setting Bot Presence '🔊 Creating Voice Channels Like A Boss 🔊'",
        )
        await self.bot.change_presence(activity=discord.Game(name="🔊 Creating Voice Channels Like A Boss 🔊"))

    @commands.Cog.listener()
    async def on_disconnect(self):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Bot Disconnected")

    @commands.Cog.listener()
    async def on_resumed(self):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Bot Session Resumed")

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        _method = inspect.stack()[0][3]
        self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(event)}", traceback.format_exc())

async def setup(bot):
    await bot.add_cog(Events(bot))
