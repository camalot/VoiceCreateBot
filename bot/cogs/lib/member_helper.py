import discord

def is_in_voice_channel(user: discord.Member) -> bool:
    return user.voice is not None and user.voice.channel is not None
