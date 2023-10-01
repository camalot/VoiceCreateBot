import inspect
import os
import traceback

from bot.cogs.lib.mongodb.database import Database
from bot.cogs.lib.enums.loglevel import LogLevel


class MigrationBase(Database):
    def __init__(self) -> None:
        super().__init__()
        _method = inspect.stack()[0][3]
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.log(
            guildId=0,
            level=LogLevel.DEBUG,
            method=f"{self._module}.{self._class}.{_method}",
            message=f"Initialized {self._class}",
        )

    def run(self) -> None:
        pass

    def needs_run(self) -> bool:
        _method = inspect.stack()[0][3]
        if self.connection is None:
            self.open()

        try:
            run = self.connection.migration_runs.find_one({"module": self._module})
            if run is None:
                return True
            else:
                return not run["completed"]
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to determine if migration needs running: {ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def track_run(self, success: bool) -> None:
        _method = inspect.stack()[0][3]
        if self.connection is None:
            self.open()

        try:
            self.connection.migration_runs.update_one(
                {"module": self._module}, {"$set": {"completed": success}}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to track migration run: {ex}",
                stackTrace=traceback.format_exc(),
            )
