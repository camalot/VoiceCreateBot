import sys
import typing

from bot.cogs.lib import loglevel, mongo
from bot.cogs.lib.colors import Colors


class Log():
    def __init__(self, minimumLogLevel: loglevel.LogLevel = loglevel.LogLevel.DEBUG):
        self.db = mongo.MongoDatabase()
        self.minimum_log_level = minimumLogLevel

    def __write(
        self,
        guildId: int,
        level: loglevel.LogLevel,
        method: str,
        message: str,
        stackTrace: typing.Optional[str] = None,
        file: typing.IO = sys.stdout,
    ):
        color = Colors.get_color(level)
        m_level = Colors.colorize(color, f"[{level.name}]", bold=True)
        m_method = Colors.colorize(Colors.HEADER, f"[{method}]", bold=False)
        m_message = f"{Colors.colorize(color, message)}"
        m_guild = Colors.colorize(Colors.OKGREEN, f"[{guildId}]", bold=False)
        str_out = f"{m_level} {m_method} {m_guild} {m_message}"
        print(str_out, file=file)
        if stackTrace:
            print(Colors.colorize(color, stackTrace), file=file)

        if level >= self.minimum_log_level:
            self.db.insert_log(guildId=guildId, level=level, method=method, message=message, stackTrace=stackTrace)

    def debug(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=loglevel.LogLevel.DEBUG,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stdout,
        )
        
    def info(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=loglevel.LogLevel.INFO,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stdout,
        )

    def warn(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=loglevel.LogLevel.WARNING,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stdout,
        )

    def error(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=loglevel.LogLevel.ERROR,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stderr,
        )

    def fatal(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=loglevel.LogLevel.FATAL,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stderr,
        )
