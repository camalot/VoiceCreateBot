class TrackedVoiceChannel:
    def __init__(self, guildId: int, ownerId: int, voiceChannelId: int):
        self.guild_id = int(guildId)
        self.owner_id = int(ownerId)
        self.voice_channel_id = int(voiceChannelId)
