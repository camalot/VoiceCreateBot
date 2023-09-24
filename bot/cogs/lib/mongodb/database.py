import inspect
import os
import sys
import traceback
import typing

from bot.cogs.lib import loglevel, settings, utils
from bot.cogs.lib.colors import Colors
from pymongo import MongoClient


class Database():
    def __init__(self):
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = settings.Settings()
        self.client = None
        self.connection = None

    def open(self):
        if not self.settings.db_url:
            raise ValueError("VCB_MONGODB_URL is not set")
        if not self.settings.db_name:
            raise ValueError("VCB_MONGODB_DBNAME is not set")

        self.client = MongoClient(self.settings.db_url)
        self.connection = self.client[self.settings.db_name]

    def close(self):
        try:
            if self.client is not None and self.connection is not None:
                self.client.close()
                self.client = None
                self.connection = None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def log(
        self,
        guildId: typing.Optional[int],
        level: loglevel.LogLevel,
        method: str,
        message: str,
        stackTrace: typing.Optional[str] = None,
        outIO: typing.Optional[typing.IO] = None,
        colorOverride: typing.Optional[str] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        if guildId is None:
            guildId = 0
        if colorOverride is None:
            color = Colors.get_color(level)
        else:
            color = colorOverride

        m_level = Colors.colorize(color, f"[{level.name}]", bold=True)
        m_method = Colors.colorize(Colors.HEADER, f"[{method}]", bold=True)
        m_guild = Colors.colorize(Colors.OKGREEN, f"[{guildId}]", bold=True)
        m_message = f"{Colors.colorize(color, message)}"

        str_out = f"{m_level} {m_method} {m_guild} {m_message}"
        if outIO is None:
            stdoe = sys.stdout if level < loglevel.LogLevel.ERROR else sys.stderr
        else:
            stdoe = outIO

        print(str_out, file=stdoe)
        if stackTrace:
            print(Colors.colorize(color, stackTrace), file=stdoe)
        try:
            if level >= loglevel.LogLevel.INFO:
                self.insert_log(guildId=guildId, level=level, method=method, message=message, stackTrace=stackTrace)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.PRINT,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
                outIO=sys.stderr,
                colorOverride=Colors.FAIL,
            )

    def insert_log(
        self,
        guildId: int,
        level: loglevel.LogLevel,
        method: str,
        message: str,
        stackTrace: typing.Optional[str] = None
    ):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": guildId,
                "timestamp": utils.get_timestamp(),
                "level": level.name,
                "method": method,
                "message": message,
                "stack_trace": stackTrace
            }
            self.connection.logs.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.PRINT,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
                outIO=sys.stderr,
                colorOverride=Colors.FAIL,
            )
