import discord
import math
import asyncio
import aiohttp
import json
from discord.ext import commands
import inspect
from random import randint
import traceback
import sys
import os
import glob
import typing
import discordhealthcheck

from bot.cogs.lib import logger, mongo, settings
from bot.cogs.lib.enums import loglevel


class VoiceCreate(commands.Bot):
    DBVERSION = 7 # CHANGED WHEN THERE ARE NEW SQL FILES TO PROCESS
    # 0 = NO SCHEMA APPLIED

    # VERSION HISTORY:
    # v1: 04/30/2020
    # v2: 07/01/2020
    # v3: 09/01/2021
    # v4: 9/9/2021 - added auto_game column to userSettings
    # v5: 9/13/2021 - rename the collections
    # v6: 9/15/2021 - added language field to guild_settings
    # v7: 7/31/2023 - Migration for app version 2.x

    def __init__(self, *, intents: discord.Intents):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            case_insensitive=True,
        )

        self.settings = settings.Settings()
        print(f"APP VERSION: {self.settings.APP_VERSION}")

        self.db = mongo.MongoDatabase()
        self.initDB()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", f"Logger initialized with level {log_level.name}")
        self.log.debug(0, f"{self._module}.{_method}", f"Initialized")



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

        # _method = inspect.stack()[0][3]
        # self.log.debug(0, f"{self._module}.{_method}", "Setup hook called")
        # # cogs that dont start with an underscore are loaded
        # cogs = [
        #     f"bot.cogs.{os.path.splitext(f)[0]}"
        #     for f in os.listdir("bot/cogs")
        #     if f.endswith(".py") and not f.startswith("_")
        # ]

        # for extension in cogs:
        #     try:
        #         await self.load_extension(extension)
        #     except Exception as e:
        #         print(f"Failed to load extension {extension}.", file=sys.stderr)
        #         traceback.print_exc()

        # self.log.debug(0, f"{self._module}.{_method}", "Setting up bot")
        # self.log.debug(0, f"{self._module}.{_method}", "Starting Healthcheck Server")
        # self.healthcheck_server = await discordhealthcheck.start(self)

    def initDB(self):
        pass
        # self.db.UPDATE_SCHEMA(self.DBVERSION)
        # sql3db = sqlite.SqliteDatabase()
        # sql3db.UPDATE_SCHEMA(self.DBVERSION)
        # mdb = mongo.MongoDatabase()
        # # mdb.RESET_MIGRATION()
        # mdb.UPDATE_SCHEMA(self.DBVERSION)

    async def get_prefix(self, message) -> typing.List[str]:
        _method: str = inspect.stack()[0][3]
        # default prefixes
        default_prefixes: typing.List[str] = [".voice ", "?voice ", "!voice ", ".vcb ", "?vcb ", "!vcb "]
        # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        prefixes: typing.List[str] =  default_prefixes
        try:
            # get the prefix for the guild.
            if message.guild:
                guild_id = message.guild.id
                # get settings from db
                prefixes = self.settings.db.get_prefixes(guild_id)
                if prefixes is None:
                    self.log.debug(guild_id, f"{self._module}.{_method}", f"Prefixes not found for guild {guild_id}. Using default prefixes")
                    prefixes = default_prefixes

                self.log.debug(guild_id, f"{self._module}.{_method}", f"Getting prefixes for guild {guild_id}: {prefixes}")
            # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
            # Do `return prefixes` if you don't want to allow mentions instead of prefix.
            print(f"prefixes: {prefixes}")
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
