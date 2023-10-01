import inspect
import os
import traceback

from bot.cogs.lib.mongodb.migration_base import MigrationBase
from bot.cogs.lib.enums.loglevel import LogLevel



class Migration(MigrationBase):
    def __init__(self):
        _method = inspect.stack()[0][3]
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        # get the description from the module name
        # <number>_<description>_migration.py
        self._number = self._module.split("_", 3)[0]
        self._description = self._module.split("_", 3)[1].replace("-", " ")

        self.log(
            guildId=0,
            level=LogLevel.DEBUG,
            method=f"{self._module}.{self._class}.{_method}",
            message=f"INITIALIZE MIGRATION {self._number} - {self._description}",
        )

    def run(self):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()

            self.log(
                guildId=0,
                level=LogLevel.DEBUG,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"EXECUTE MIGRATION {self._number}",
            )
            # v8 migration start
            collections = self.connection.list_collection_names()
            if "migration" in collections:
                self.connection.migration.drop()

            self.log(
                guildId=0,
                level=LogLevel.DEBUG,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"COMPLETE MIGRATION {self._number}",
            )
            self.track_run(True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to run migration: {ex}",
                stackTrace=traceback.format_exc(),
            )
            self.track_run(False)
