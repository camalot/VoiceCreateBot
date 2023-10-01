import inspect
import os
import sys
import traceback
from bot.cogs.lib.mongodb.databasebase import DatabaseBase
from bot.cogs.lib.settings import Settings


class Database(DatabaseBase):
    def __init__(self):
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = Settings()

        self.db_url = self.settings.db_url
        self.db_name = self.settings.db_name
