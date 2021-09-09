import sys
import os
import traceback
import glob
import typing
from . import utils
import json

class Settings:
    APP_VERSION = "1.0.0-snapshot"
    BITRATE_DEFAULT = 64

    def __init__(self):
        try:
            with open('app.manifest') as json_file:
                self.__dict__.update(json.load(json_file))
        except Exception as e:
            print(e, file=sys.stderr)
        self.db_path = utils.dict_get(os.environ, 'VCB_DB_PATH', default_value = 'voice.db')
        self.db_url = utils.dict_get(os.environ, "VCB_MONGODB_URL", default_value="")

        self.admin_roles = utils.dict_get(os.environ, 'ADMIN_ROLES', default_value = 'Admin').split(',')
        self.admin_users = utils.dict_get(os.environ, 'ADMIN_USERS', default_value = 'Admin').split(' ')
        self.default_role = utils.dict_get(os.environ, 'DEFAULT_ROLE', default_value= '@everyone')
        self.bot_owner = utils.dict_get(os.environ, 'BOT_OWNER', default_value= '262031734260891648')

class GuildCategorySettings:
    def __init__(self, guildId, categoryId, channelLimit, channelLocked, bitrate, defaultRole):
        self.guild_id = guildId
        self.category_id = categoryId
        self.channel_limit = channelLimit
        self.channel_locked = channelLocked >= 1
        self.bitrate = bitrate
        self.default_role = defaultRole
class UserSettings():
    def __init__(self, guildId, userId, channelName, channelLimit, bitrate, defaultRole):
        self.user_id = userId
        self.channel_name = channelName
        self.channel_limit = channelLimit
        self.bitrate = bitrate
        self.default_role = defaultRole
        pass

class GuildSettings:
    def __init__(self, guildId, prefix, defaultRole, adminRole):
        self.guild_id = guildId
        self.default_role = defaultRole
        self.admin_role = adminRole
        self.prefix = prefix
class GuildCreateChannelSettings:
    def __init__(self, guildId):
        self.guild_id = guildId
        self.channels = []
        pass
class GuildCategoryChannel:
    def __init__(self, ownerId, categoryId, channelId, useStage):
        self.owner_id = int(ownerId)
        self.category_id = int(categoryId)
        self.channel_id = int(channelId)
        self.use_stage = useStage >= 1
class TrackedVoiceChannel:
    def __init__(self, guildId, ownerId, voiceChannelId):
        self.guild_id = int(guildId)
        self.owner_id = int(ownerId)
        self.voice_channel_id = int(voiceChannelId)

class TrackedTextChannel(TrackedVoiceChannel):
    def __init__(self, guildId, ownerId, voiceChannelId, textChannelId):
        super(TrackedTextChannel, self).__init__(guildId=guildId, ownerId=ownerId, voiceChannelId=voiceChannelId)
        self.text_channel_id = int(textChannelId)

class TrackedChannels:
    def __init__(self, voiceChannels, textChannels):
        self.voice_channels = voiceChannels
        self.text_channels = textChannels
