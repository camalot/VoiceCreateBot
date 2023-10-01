import inspect
import os
import traceback
import typing

from bot.cogs.lib.mongodb.database import Database
from bot.cogs.lib.enums.loglevel import LogLevel

class ExporterMongoDatabase(Database):

    def __init__(self):
        _method = inspect.stack()[0][3]
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def get_guilds(self) -> typing.Optional[typing.Iterable[dict[str, typing.Any]]]:
        """Get all guilds"""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            return self.connection.guilds.find()
        except Exception as e:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{e}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def get_user_settings_count(self) -> typing.Optional[typing.Iterable[dict[str, typing.Any]]]:
        """Get all user settings"""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            return self.connection.user_settings.aggregate([
                {"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}
            ])
        except Exception as e:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{e}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def get_tracked_channel_history(self) -> typing.Optional[typing.Iterable[dict[str, typing.Any]]]:
        """Get all tracked channels"""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            return self.connection.tracked_channel_history.aggragate([
                {
                    "$group": {
                        "_id": {"guild_id": "$guild_id", "user_id": "$user_id"},
                        "total": {"$sum": 1}
                    }
                }
            ])
        except Exception as e:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{e}",
                stackTrace=traceback.format_exc(),
            )
            return None
