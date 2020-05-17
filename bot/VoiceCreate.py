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
from dotenv import load_dotenv, find_dotenv
import glob
import typing
from .cogs.lib import utils
from .cogs.lib import settings

class VoiceCreate():
    DISCORD_TOKEN = os.environ['DISCORD_BOT_TOKEN']
    DBVERSION = 1 # CHANGED WHEN THERE ARE NEW SQL FILES TO PROCESS
    # 0 = NO SCHEMA APPLIED

    # VERSION HISTORY:
    # v1: 04/30/2020
    # v2: 5/16/2020

    def __init__(self):
        load_dotenv(find_dotenv())
        self.settings = settings.Settings()
        print(f"APP VERSION: {self.settings.APP_VERSION}")
        print(f"DBPath: {self.settings.db_path}")
        self.initDB()
        self.client = discord.Client()

        self.bot = commands.Bot(
            command_prefix=self.get_prefix,
            case_insensitive=True
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
        conn = sqlite3.connect(self.settings.db_path)
        try:
            dbversion = utils.get_scalar_result(conn, "PRAGMA user_version", 0)
            c = conn.cursor()
            print(f"LOADED SCHEMA VERSION: {dbversion}")
            print(f"CURRENT SCHEMA VERSION: {self.DBVERSION}")
            for x in range(0, self.DBVERSION+1):
                files = glob.glob(f"sql/{x:04d}.*.sql")
                for f in files:
                    if dbversion == 0 or dbversion < x:
                        print(f"Applying SQL: {f}")
                        file = open(f, mode='r')
                        contents = file.read()
                        c.executescript(contents)
                        conn.commit()
                        file.close()
                    else:
                        print(f"Skipping SQL: {f}")
            if dbversion < self.DBVERSION:
                print(f"Updating SCHEMA Version to {self.DBVERSION}")
                c.execute(f"PRAGMA user_version = {self.DBVERSION}")
                conn.commit()
            c.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.close()

    def get_prefix(self, client, message):
        prefixes = ['.']    # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        if not message.guild:
            prefixes = ['.']   # Only allow '.' as a prefix when in DMs, this is optional
        # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
        # Do `return prefixes` if you don't want to allow mentions instead of prefix.
        return commands.when_mentioned_or(*prefixes)(client, message)
