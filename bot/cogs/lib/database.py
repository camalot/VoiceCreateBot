
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

    def get_channel_owner_id(self, guildId, voiceChannelId):
        # c.execute("SELECT userID FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildID, after.id,))
        pass
    def get_user_settings(self, guildId, userId):
        pass
    def get_guild_settings(self, guildId):
        pass
    def get_guild_category_settings(self, guildId, categoryId):
        pass
    def update_user_channel_name(self, guildId, userId, channelName):
        pass
    def insert_user_settings(self, guildId, userId, channelName, channelLimit, bitrate, defaultRole):
        pass
