import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import math
import datetime

import inspect

from .lib import settings
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib.mongodb.users import UsersMongoDatabase
class UserTrackingCog(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.db = UsersMongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    # on events, get the user id and username and store it in the database
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        _method = inspect.stack()[0][3]
        try:
            if member is None or member.guild is None:
                return
            self.log.debug(member.guild.id, f"{self._module}.{_method}", f"User {member.id} joined guild {member.guild.id}")
            self.db.track_user(member)
        except Exception as e:
            self.log.error(member.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before, after) -> None:
        _method = inspect.stack()[0][3]
        try:
            if after is None or after.guild is None:
                return
            self.log.debug(after.guild.id, f"{self._module}.{_method}", f"User {after.id} updated in guild {after.guild.id}")
            self.db.track_user(after)
        except Exception as e:
            self.log.error(after.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())


async def setup(bot):
    await bot.add_cog(UserTrackingCog(bot))
