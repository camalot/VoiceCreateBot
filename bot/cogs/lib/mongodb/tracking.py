import datetime
import inspect
import os
import traceback
import typing

import discord
from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.database import Database
from bot.cogs.lib.enums.system_actions import SystemActions



class TrackingDatabase(Database):

    def __init__(self):
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

    def track_system_action(self, guildId: int, userId: int, action: SystemActions):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "action": action.name,
                "timestamp": utils.get_timestamp()
            }
            self.connection.system_actions.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
    def track_command(self, guildId: int, userId: int, command: str, args: typing.Optional[dict] = None):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "command": command,
                "args": args,
                "timestamp": utils.get_timestamp()
            }
            self.connection.commands.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
