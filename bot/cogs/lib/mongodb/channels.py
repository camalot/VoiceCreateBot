import inspect
import traceback
import os
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
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

    def get_tracked_channel_owner(self, guildId: int, voiceChannelId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            owner = self.connection.voice_channels.find_one(
                {"guild_id": str(guildId), "voice_id": str(voiceChannelId)}, {"user_id": 1}
            )
            if owner:
                return owner['user_id']
            return None
        except Exception as ex:
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )

    def update_tracked_channel_owner(
            self,
            guildId: int,
            voiceChannelId: typing.Optional[int],
            ownerId: typing.Optional[int],
            newOwnerId: typing.Optional[int],
        ):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            self.connection.voice_channels.update_one(
                {"guild_id": str(guildId), "voice_id": str(voiceChannelId), "user_id": str(ownerId)},
                {"$set": {"user_id": str(newOwnerId)}},
            )
            self.connection.text_channels.update_one(
                {"guild_id": str(guildId), "voice_id": str(voiceChannelId), "user_id": str(ownerId)},
                {"$set": {"user_id": str(newOwnerId)}},
            )
        except Exception as ex:
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )

    def get_channel_owner_id(self, guildId: int, channelId: typing.Optional[int]):
        _method = inspect.stack()[0][3]
        try:
            if channelId is None:
                return None
            if self.connection is None:
                self.open()
            item = self.connection.voice_channels.find_one({"guild_id": str(guildId), "voice_id": channelId}, {"user_id": 1})
            if item:
                return int(item['user_id'])
            item = self.connection.text_channels.find_one({"guild_id": str(guildId), "channel_id": channelId}, {"user_id": 1})
            if item:
                return int(item['user_id'])
            return None
        except Exception as ex:
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )

    def get_text_channel_id(self, guildId: int, voiceChannelId: int) -> typing.Optional[int]:
        try:
            if self.connection is None:
                self.open()
            result = self.connection.text_channels.find_one({"guild_id": str(guildId), "voice_id": str(voiceChannelId)})
            if result:
                return result['channel_id']
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tracked_voice_channel_id_by_owner(self, guildId: int, ownerId: typing.Optional[int]) -> typing.List[int]:
        try:
            if ownerId is None:
                return []
            if self.connection is None:
                self.open()
            # c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ? AND userID = ?", (guildId, ownerId,))
            items = self.connection.voice_channels.find({"guild_id": str(guildId), "user_id": str(ownerId)}, {"voice_id": 1})
            channel_ids = [item['voice_id'] for item in items]
            return channel_ids
        except Exception as ex:
            raise ex
