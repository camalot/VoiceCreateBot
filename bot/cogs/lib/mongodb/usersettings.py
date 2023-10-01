import traceback
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.models.user_settings import UserSettings
from bot.cogs.lib.mongodb.database import Database


class UserSettingsDatabase(Database):
    def __init__(self):
        super().__init__()
        pass

    def get_user_settings(self, guildId: int, userId: typing.Optional[int]):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (userId, guildId,))
            r = self.connection.user_settings.find_one({"guild_id": str(guildId), "user_id": str(userId)})
            if r:
                return UserSettings(
                    guildId=guildId,
                    userId=int(userId) if userId is not None else 0,
                    channelName=r['channel_name'],
                    channelLimit=int(r['channel_limit']),
                    bitrate=int(r['bitrate']),
                    defaultRole=r['default_role'],
                    autoGame=r['auto_game'],
                )
            else:
                return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def update_user_channel_name(self, guildId: int, userId: typing.Optional[int], channelName: typing.Optional[str]):
        try:
            if userId is None or channelName is None:
                return

            if self.connection is None:
                self.open()
            # c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
            self.connection.user_settings.find_one_and_update(
                {"guild_id": str(guildId), "user_id": str(userId)}, {"$set": {"channel_name": channelName}}
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def insert_user_settings(
            self,
            guildId: int,
            userId: typing.Optional[int],
            channelName: str,
            channelLimit: int,
            bitrate: int,
            defaultRole: int,
            autoGame: bool = False,
        ):
        try:
            if userId is None:
                return

            if self.connection is None:
                self.open()
            # c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "channel_name": channelName,
                "channel_limit": channelLimit,
                "bitrate": bitrate,
                "default_role": defaultRole,
                "auto_game": autoGame,
                "timestamp": utils.get_timestamp()
            }
            self.connection.user_settings.insert_one(payload)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
