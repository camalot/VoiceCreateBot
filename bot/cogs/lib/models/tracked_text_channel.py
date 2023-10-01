from bot.cogs.lib.models.tracked_voice_channel import TrackedVoiceChannel

class TrackedTextChannel(TrackedVoiceChannel):
    def __init__(self, guildId: int, ownerId: int, voiceChannelId: int, textChannelId: int):
        super(TrackedTextChannel, self).__init__(guildId=guildId, ownerId=ownerId, voiceChannelId=voiceChannelId)
        self.text_channel_id = int(textChannelId)
