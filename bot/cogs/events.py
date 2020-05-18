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

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        print(f"DB Path: {self.settings.db_path}")


    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print('Logged in as')
        print(self.bot.user.name)
        print(self.bot.user.id)
        print('------')
        print(f"Setting Bot Presence")
        await self.bot.change_presence(activity=discord.Game(name="🔊 Creating Voice Channels Like A Boss 🔊"))
        print('------')

    @commands.Cog.listener()
    async def on_disconnect(self):
        print('------')
        print('Bot Disconnected')
        print('------')

    @commands.Cog.listener()
    async def on_resumed(self):
        print('------')
        print('Bot Session Resumed')
        print('------')

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        print('------')
        print('On Error')
        print(event)
        traceback.print_exc()
        print('------')

def setup(bot):
    bot.add_cog(Events(bot))
