import sys
import os
import traceback
import glob
import typing
from . import utils
import json
from . import dbprovider

class Settings:
    APP_VERSION = "1.0.0-snapshot"
    BITRATE_DEFAULT = 64

    def __init__(self):
        try:
            with open('app.manifest') as json_file:
                self.__dict__.update(json.load(json_file))
        except Exception as e:
            print(e, file=sys.stderr)
        self.db_url = utils.dict_get(os.environ, "VCB_MONGODB_URL", default_value="")
        self.db_path = utils.dict_get(os.environ, 'VCB_DB_PATH', default_value = 'voice.db')

        self.bot_owner = utils.dict_get(os.environ, 'BOT_OWNER', default_value= '262031734260891648')
        self.log_level = utils.dict_get(os.environ, 'LOG_LEVEL', default_value = 'DEBUG')
        dbp = utils.dict_get(os.environ, 'DB_PROVIDER', default_value = 'DEFAULT').upper()
        self.db_provider = dbprovider.DatabaseProvider[dbp]
        if not self.db_provider:
            self.db_provider = dbprovider.DatabaseProvider.DEFAULT


        # DEPRECATED
        # self.admin_roles = utils.dict_get(os.environ, 'ADMIN_ROLES', default_value = 'Admin').split(',')
        # self.admin_users = utils.dict_get(os.environ, 'ADMIN_USERS', default_value = '').split(' ')



class GuildCategorySettings:
    def __init__(self, guildId: int, categoryId: int, channelLimit: int, channelLocked: bool, bitrate: int, defaultRole: typing.Union[str, int] ):
        self.guild_id = guildId
        self.category_id = categoryId
        self.channel_limit = channelLimit
        self.channel_locked = channelLocked >= 1
        self.bitrate = bitrate
        self.default_role = defaultRole

class UserSettings():
    def __init__(self, guildId: int, userId: int, channelName: str, channelLimit: int, bitrate: int, defaultRole: typing.Union[str, int], autoGame: bool):
        self.user_id = userId
        self.channel_name = channelName
        self.channel_limit = channelLimit
        self.bitrate = bitrate
        self.default_role = defaultRole
        self.auto_game = autoGame
        pass

class GuildSettings:
    def __init__(self, guildId: int, prefix, defaultRole: int, adminRole: int):
        self.guild_id = guildId
        self.default_role = defaultRole
        self.admin_role = adminRole
        self.prefix = prefix

class GuildCreateChannelSettings:
    def __init__(self, guildId: int):
        self.guild_id = guildId
        self.channels = []

class GuildCategoryChannel:
    def __init__(self, ownerId: int, categoryId: int, channelId: int, useStage: bool):
        self.owner_id = int(ownerId)
        self.category_id = int(categoryId)
        self.channel_id = int(channelId)
        self.use_stage = useStage >= 1

class TrackedVoiceChannel:
    def __init__(self, guildId: int, ownerId: int, voiceChannelId: int):
        self.guild_id = int(guildId)
        self.owner_id = int(ownerId)
        self.voice_channel_id = int(voiceChannelId)

class TrackedTextChannel(TrackedVoiceChannel):
    def __init__(self, guildId: int, ownerId: int, voiceChannelId: int, textChannelId: int):
        super(TrackedTextChannel, self).__init__(guildId=guildId, ownerId=ownerId, voiceChannelId=voiceChannelId)
        self.text_channel_id = int(textChannelId)

class TrackedChannels:
    def __init__(self, voiceChannels: list[TrackedVoiceChannel], textChannels: list[TrackedTextChannel]):
        self.voice_channels = voiceChannels
        self.text_channels = textChannels
