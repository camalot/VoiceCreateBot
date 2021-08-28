
class Database():

    def __init__(self):
        pass
    def open(self):
        pass
    def close(self):
        pass
    def get_tracked_voice_channel_ids(self, guildId):
        # SELECT voiceID FROM voiceChannel WHERE guildID = ?
        pass

    def get_text_channel_id(self, guildId, voiceChannelId):
        # SELECT channelID FROM textChannel WHERE guildID = ? and voiceId = ?
        pass

    def clean_tracked_channels(self, guildId, voiceChannelId, textChannelId):
        # c.execute('DELETE FROM voiceChannel WHERE guildID = ? and voiceId = ?', (guildID, voiceChannelId,))
        # c.execute('DELETE FROM textChannel WHERE guildID = ? and channelID = ?', (guildID, textChannelId,))
        pass
