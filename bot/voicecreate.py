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
class VoiceCreate():
    DISCORD_TOKEN = os.environ['DISCORD_BOT_TOKEN']
    DBVERSION = 3 # CHANGED WHEN THERE ARE NEW SQL FILES TO PROCESS
    # 0 = NO SCHEMA APPLIED

    # VERSION HISTORY:
    # v1: 04/30/2020
    # v2: 07/01/2020
    # v3: 09/01/2021

    def __init__(self):
        self.settings = settings.Settings()
        print(f"APP VERSION: {self.settings.APP_VERSION}")
        print(f"DBPath: {self.settings.db_path}")
        self.initDB()
        self.client = discord.Client()

        # loop all guilds and init per guild???

        self.bot = commands.Bot(
            command_prefix=self.get_prefix,
            case_insensitive=True,
            intents=discord.Intents.all()
        )

        initial_extensions = ['bot.cogs.events', 'bot.cogs.voice']
        for extension in initial_extensions:
            try:
                self.bot.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

        self.bot.remove_command("help")
        self.bot.run(self.DISCORD_TOKEN)

    def initDB(self):
        sql3db = sqlite.SqliteDatabase()
        sql3db.UPDATE_SCHEMA(self.DBVERSION)
        mdb = mongo.MongoDatabase()
        # mdb.RESET_MIGRATION()
        mdb.UPDATE_SCHEMA(self.DBVERSION)

    def get_prefix(self, client, message):
        # get the prefix for the guild.

        prefixes = ['.']    # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        if not message.guild:
            prefixes = ['.']   # Only allow '.' as a prefix when in DMs, this is optional
        # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
        # Do `return prefixes` if you don't want to allow mentions instead of prefix.
        return commands.when_mentioned_or(*prefixes)(client, message)
