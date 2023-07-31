from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import bot.voicecreate as vc
import discord
import os


def main():
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

if __name__ == '__main__':
    main()
