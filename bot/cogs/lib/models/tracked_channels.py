import typing

from bot.cogs.lib.models.tracked_voice_channel import TrackedVoiceChannel
from bot.cogs.lib.models.tracked_text_channel import TrackedTextChannel

class TrackedChannels:
    def __init__(self, voiceChannels: typing.List[TrackedVoiceChannel], textChannels: typing.List[TrackedTextChannel]):
        self.voice_channels = voiceChannels
        self.text_channels = textChannels
