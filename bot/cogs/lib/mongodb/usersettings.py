import inspect
import traceback
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.models.user_settings import UserSettings
from bot.cogs.lib.enums.loglevel import LogLevel
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
                    channelLocked=r['channel_locked'],
                    bitrate=int(r['bitrate']),
                    defaultRole=r['default_role'],
                    autoGame=r['auto_game'],
                    autoName=r['auto_name'],
                    allowSoundboard=r['allow_soundboard'],
                )
            else:
                return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def update_user_channel_name(self, guildId: int, userId: typing.Optional[int], channelName: typing.Optional[str]):
        _method = inspect.stack()[1][3]
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
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )

    def insert_user_settings(
            self,
            guildId: int,
            userId: typing.Optional[int],
            channelName: str,
            channelLimit: int,
            channelLocked: bool,
            bitrate: int,
            defaultRole: int,
            autoGame: bool = False,
            autoName: bool = True,
            allowSoundboard: bool = False,
        ):
        _method = inspect.stack()[1][3]
        try:
            if userId is None:
                return

            if self.connection is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "channel_name": channelName,
                "channel_limit": channelLimit,
                "channel_locked": channelLocked,
                "bitrate": bitrate,
                "default_role": str(defaultRole),
                "auto_game": autoGame,
                "auto_name": autoName,
                "allow_soundboard": allowSoundboard,
                "timestamp": utils.get_timestamp()
            }
            self.connection.user_settings.insert_one(payload)

        except Exception as ex:
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )
