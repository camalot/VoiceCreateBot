import inspect
import os
import traceback
import typing

from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.database import Database


class LogsMongoDatabase(Database):
    def __init__(self):
        super().__init__()
        _method = inspect.stack()[0][3]
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

    def clear_log(self, guildId):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            self.connection.logs.delete_many({ "guild_id": guildId })
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
