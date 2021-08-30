
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
    def get_tracked_voice_channel_id_by_owner(self, guildId, ownerId):
        pass
    def get_channel_owner_id(self, guildId, voiceChannelId):
        pass
    def get_user_settings(self, guildId, userId):
        pass
    def get_guild_settings(self, guildId):
        pass
    def set_guild_category_settings(self, guildId, categoryId, channelLimit, channelLocked, bitrate, defaultRole):
        pass
    def get_guild_category_settings(self, guildId, categoryId):
        pass
    def update_user_channel_name(self, guildId, userId, channelName):
        pass
    def insert_user_settings(self, guildId, userId, channelName, channelLimit, bitrate, defaultRole):
        pass
    def get_guild_create_channels(self, guildId):
        pass
    def get_use_stage_on_create(self, guildId, channelId, categoryId):
        pass
    def add_tracked_text_channel(self, guildId, ownerId, voiceChannelId, textChannelId):
        pass
    def delete_tracked_text_channel(self, guildId, voiceChannelId, textChannelId):
        pass
    def track_new_voice_channel(self, guildId, ownerId, voiceChannelId):
        pass
    def track_new_channel_set(self, guildId, ownerId, voiceChannelId, textChannelId):
        pass
    def get_tracked_channels_for_guild(self, guildId):
        pass
    def get_tracked_channel_owner(self, guildId, voiceChannelId):
        pass
    def clean_guild_user_settings(self, guildId):
        pass
    def get_default_role(self, guildId, categoryId, userId):
        pass
    def set_default_role_for_user(self, guildId, userId, defaultRole):
        pass
    def set_default_role_for_category(self, guildId, categoryId, defaultRole):
        pass
