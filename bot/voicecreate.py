import discord
import math
import asyncio
import aiohttp
import json
from discord.ext import commands

from random import randint
import traceback
import sqlite3
import sys
import os
import glob
import typing
from .cogs.lib import utils
from .cogs.lib import settings
from .cogs.lib import sqlite
from .cogs.lib import mongo
from .cogs.lib import logger
from .cogs.lib import loglevel
from .cogs.lib import dbprovider
from discord_slash import SlashCommand

class VoiceCreate():
    DISCORD_TOKEN = os.environ['DISCORD_BOT_TOKEN']
    DBVERSION = 4 # CHANGED WHEN THERE ARE NEW SQL FILES TO PROCESS
    # 0 = NO SCHEMA APPLIED

    # VERSION HISTORY:
    # v1: 04/30/2020
    # v2: 07/01/2020
    # v3: 09/01/2021
    # v4: 9/9/2021 - added auto_game column to userSettings
    def __init__(self):
        self.settings = settings.Settings()
        print(f"APP VERSION: {self.settings.APP_VERSION}")
        print(f"DBPath: {self.settings.db_path}")
        self.initDB()
        self.client = discord.Client()

        if self.settings.db_provider == dbprovider.DatabaseProvider.SQLITE:
            self.db = sqlite.SqliteDatabase()
        elif self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "voice.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "voice.__init__", f"Logger initialized with level {log_level.name}")

        self.bot = commands.Bot(
            command_prefix=self.get_prefix,
            case_insensitive=True,
            intents=discord.Intents.all()
        )

        initial_extensions = ['bot.cogs.events', 'bot.cogs.voice', 'bot.cogs.slash']
        for extension in initial_extensions:
            try:
                self.bot.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

        slash = SlashCommand(self.bot, override_type = True, sync_commands = True)

        self.bot.remove_command("help")
        self.bot.run(self.DISCORD_TOKEN)

    def initDB(self):
        sql3db = sqlite.SqliteDatabase()
        sql3db.UPDATE_SCHEMA(self.DBVERSION)
        mdb = mongo.MongoDatabase()
        # mdb.RESET_MIGRATION()
        mdb.UPDATE_SCHEMA(self.DBVERSION)

    def get_prefix(self, client, message):
        self.db.open()
        # get the prefix for the guild.
        prefixes = ['.']    # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        if message.guild:
            guild_settings = self.db.get_guild_settings(message.guild.id)
            if guild_settings:
                prefixes = guild_settings.prefix or "."
        elif not message.guild:
            prefixes = ['.']   # Only allow '.' as a prefix when in DMs, this is optional

        # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
        # Do `return prefixes` if you don't want to allow mentions instead of prefix.
        return commands.when_mentioned_or(*prefixes)(client, message)
