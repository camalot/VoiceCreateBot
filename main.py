from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import bot.voicecreate as vc
import discord
import os
import signal
import asyncio

from bot.cogs.lib.colors import Colors
from metrics.exporter import MetricsExporter
from concurrent.futures import ProcessPoolExecutor

def sighandler(signum, frame):
    print(Colors.colorize(Colors.FGYELLOW,"<SIGTERM received>"))
    exit(0)


def main():
    try:
        DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
        intents = discord.Intents.all()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True

        voiceCreate = vc.VoiceCreate(intents=intents)
        voiceCreate.remove_command('help')
        voiceCreate.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print(Colors.colorize(Colors.FGYELLOW,"<KeyboardInterrupt received>"))
        exit(0)

def exporter():
    try:
        exporter = MetricsExporter()
        exporter.run()
    except KeyboardInterrupt:
        print(Colors.colorize(Colors.FGYELLOW,"<KeyboardInterrupt received>"))
        exit(0)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    signal.signal(signal.SIGTERM, sighandler)
    try:
        executor = ProcessPoolExecutor(2)
        loop.run_in_executor(executor, main)
        loop.run_in_executor(executor, exporter)
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
