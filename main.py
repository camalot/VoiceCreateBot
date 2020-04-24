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

client = discord.Client()

bot = commands.Bot(command_prefix=".")
bot.remove_command("help")
DISCORD_TOKEN = os.environ['DISCORD_BOT_TOKEN']

initial_extensions = ['cogs.voice']

if __name__ == '__main__':
    load_dotenv(find_dotenv())
    print(os.environ['VCB_DB_PATH'])
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()

@bot.event
async def on_ready():
    print('------')
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.event
async def on_disconnect():
    print('------')
    print('Bot Disconnected')
    print('------')

@bot.event
async def on_error(event, *args, **kwargs):
    print('------')
    print('On Error')
    print(event)
    traceback.print_exc()
    print('------')

bot.run(DISCORD_TOKEN)
