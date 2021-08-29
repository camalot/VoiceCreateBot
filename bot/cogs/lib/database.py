
class Database():

    def __init__(self):
        pass
    def open(self):
        pass
    def close(self):
        pass
    def get_tracked_voice_channel_ids(self, guildId):
        pass

    def get_text_channel_id(self, guildId, voiceChannelId):
        pass
    def get_voice_channel_id_from_text_channel(self, guildId, textChannelId):
        pass

    def clean_tracked_channels(self, guildId, voiceChannelId, textChannelId):
        pass

    def get_channel_owner_id(self, guildId, voiceChannelId):
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
