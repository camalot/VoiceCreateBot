from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
import bot.voicecreate as vc
import discord
import os
import signal
import asyncio

from bot.cogs.lib.mongodb.migration_runner import MigrationRunner
from bot.cogs.lib.colors import Colors
from metrics.exporter import MetricsExporter
from concurrent.futures import ProcessPoolExecutor

def sighandler(signum: int, frame):
    match signum:
        case signal.SIGTERM:
            print(Colors.colorize(Colors.FGYELLOW, "<SIGTERM received>"))
        case signal.SIGINT:
            print(Colors.colorize(Colors.FGYELLOW, "<SIGINT received>"))
    exit(0)


def main():
    try:
        migrations = MigrationRunner()
        migrations.start_migrations()

        DISCORD_TOKEN = os.environ.get("VCB_DISCORD_BOT_TOKEN", "")
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
        print(Colors.colorize(Colors.FGYELLOW, "<KeyboardInterrupt received>"))
        exit(0)

def exporter():
    try:
        EXPORTER_ENABLED = os.environ.get("VCBE_CONFIG_METRICS_ENABLED", "false").lower() == "true"
        if EXPORTER_ENABLED:
            exporter = MetricsExporter()
            exporter.run()
        else:
            print(Colors.colorize(Colors.FGYELLOW, "<Metrics exporter disabled>"))
    except KeyboardInterrupt:
        print(Colors.colorize(Colors.FGYELLOW, "<KeyboardInterrupt received>"))
        exit(0)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        signal.signal(signal.SIGTERM, sighandler)
        signal.signal(signal.SIGINT, sighandler)

        executor = ProcessPoolExecutor(2)
        loop.run_in_executor(executor, main)
        loop.run_in_executor(executor, exporter)
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
