import discord
import math
import asyncio
import aiohttp
import json
from discord.ext import commands
import inspect
from random import randint
import traceback
import sqlite3
import sys
import os
import glob
import typing
import discordhealthcheck
from .cogs.lib import utils
from .cogs.lib import settings
from .cogs.lib import sqlite
from .cogs.lib import mongo
from .cogs.lib import logger
from .cogs.lib import loglevel


class VoiceCreate(commands.Bot):
    DISCORD_TOKEN = os.environ['DISCORD_BOT_TOKEN']
    DBVERSION = 6 # CHANGED WHEN THERE ARE NEW SQL FILES TO PROCESS
    # 0 = NO SCHEMA APPLIED

    # VERSION HISTORY:
    # v1: 04/30/2020
    # v2: 07/01/2020
    # v3: 09/01/2021
    # v4: 9/9/2021 - added auto_game column to userSettings
    # v5: 9/13/2021 - rename the collections
    # v6: 9/15/2021 - added language field to guild_settings
    def __init__(self, *, intents: discord.Intents):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        super().__init__(command_prefix=self.get_prefix, intents=intents, case_insensitive=True)
        self.settings = settings.Settings()
        print(f"APP VERSION: {self.settings.APP_VERSION}")
        print(f"DBPath: {self.settings.db_path}")

        self.db = mongo.MongoDatabase()
        self.initDB()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "voice.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "voice.__init__", f"Logger initialized with level {log_level.name}")

        initial_extensions = ['bot.cogs.events', 'bot.cogs.voice', 'bot.cogs.slash']
        for extension in initial_extensions:
            try:
                self.bot.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

        self.bot.remove_command("help")
        self.bot.run(self.DISCORD_TOKEN)

    async def setup_hook(self) -> None:
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{_method}", "Setup hook called")
        # cogs that dont start with an underscore are loaded
        cogs = [
            f"bot.cogs.{os.path.splitext(f)[0]}"
            for f in os.listdir("bot/cogs")
            if f.endswith(".py") and not f.startswith("_")
        ]

        for extension in cogs:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f"Failed to load extension {extension}.", file=sys.stderr)
                traceback.print_exc()

        self.log.debug(0, f"{self._module}.{_method}", "Setting up bot")
        self.log.debug(0, f"{self._module}.{_method}", "Starting Healthcheck Server")
        self.healthcheck_server = await discordhealthcheck.start(self)

    def initDB(self):
        self.db.UPDATE_SCHEMA(self.DBVERSION)
        # sql3db = sqlite.SqliteDatabase()
        # sql3db.UPDATE_SCHEMA(self.DBVERSION)
        # mdb = mongo.MongoDatabase()
        # # mdb.RESET_MIGRATION()
        # mdb.UPDATE_SCHEMA(self.DBVERSION)

    async def get_prefix(self, message) -> typing.List[str]:
        _method: str = inspect.stack()[0][3]
        # default prefixes
        # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        prefixes: typing.List[str] = [".voice ", "?voice ", "!voice "]
        try:
            # get the prefix for the guild.
            # if message.guild:
                # guild_id = message.guild.id
                # get settings from db
                # settings = self.settings.get_settings(self.db, guild_id, "tacobot")
                # if not settings:
                #     raise Exception("No bot settings found")
                # prefixes = settings["command_prefixes"]

            # elif not message.guild:
                # get the prefix for the DM using 0 for the guild_id
                # settings = self.settings.get_settings(self.db, 0, "tacobot")
                # if not settings:
                #     raise Exception("No bot settings found")
                # prefixes = settings["command_prefixes"]
            # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
            # Do `return prefixes` if you don't want to allow mentions instead of prefix.
            return commands.when_mentioned_or(*prefixes)(self, message)
        except Exception as e:
            self.log.error(0, f"{self._module}.{_method}", f"Failed to get prefixes: {e}")
            return commands.when_mentioned_or(*prefixes)(self, message)

        # self.db.open()
        # # get the prefix for the guild.
        # prefixes = ['.']    # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        # if message.guild:
        #     guild_settings = self.db.get_guild_settings(message.guild.id)
        #     if guild_settings:
        #         prefixes = guild_settings.prefix or "."
        # elif not message.guild:
        #     prefixes = ['.']   # Only allow '.' as a prefix when in DMs, this is optional

        # # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
        # # Do `return prefixes` if you don't want to allow mentions instead of prefix.
        # return commands.when_mentioned_or(*prefixes)(self, message)
