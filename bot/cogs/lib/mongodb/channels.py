import inspect
import traceback
import os
import typing

from bot.cogs.lib import loglevel, utils
from bot.cogs.lib.mongodb.database import Database
from pymongo import MongoClient

class ChannelsDatabase(Database):
    def __init__(self):
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

        self.db_url = utils.dict_get(os.environ, "VCB_MONGODB_URL", default_value="")
        self.db_name = utils.dict_get(os.environ, "VCB_MONGODB_DBNAME", default_value="voicecreate_v2")

        self.client: typing.Optional[MongoClient] = None
        self.connection: typing.Optional[typing.Any] = None
        pass

    def get_tracked_channel_owner(self, guildId, voiceChannelId):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            owner = self.connection.voice_channels.find_one(
                {"guildID": guildId, "voiceID": voiceChannelId}, { "userID": 1 }
            )
            if owner:
                return owner['userID']
            return None
        except Exception as ex:
            self.log(
                guildId,
                loglevel.LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )

    def update_tracked_channel_owner(self, guildId, voiceChannelId, ownerId, newOwnerId):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            self.connection.voice_channels.update_one(
                {"guildID": guildId, "voiceID": voiceChannelId, "userID": ownerId}, {"$set": { "userID": newOwnerId }}
            )
            self.connection.text_channels.update_one(
                {"guildID": guildId, "voiceID": voiceChannelId, "userID": ownerId}, {"$set": { "userID": newOwnerId }}
            )
        except Exception as ex:
            self.log(
                guildId,
                loglevel.LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )

    def get_channel_owner_id(self, guildId, channelId):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            item = self.connection.voice_channels.find_one({"guildID": guildId, "voiceID": channelId}, {"userID": 1})
            if item:
                return int(item['userID'])
            item = self.connection.text_channels.find_one({"guildID": guildId, "channelID": channelId}, {"userID": 1})
            if item:
                return int(item['userID'])
            return None
        except Exception as ex:
            self.log(
                guildId,
                loglevel.LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )

    def get_text_channel_id(self, guildId, voiceChannelId):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.text_channels.find_one({"guildID": guildId, "voiceID": voiceChannelId})
            if result:
                return result['channelID']
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
