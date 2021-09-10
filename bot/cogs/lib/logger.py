from . import mongo
from . import loglevel

class Log():
    def __init__(self, minimumLogLevel: loglevel.LogLevel = loglevel.LogLevel.DEBUG):
        self.db = mongo.MongoDatabase()
        self.minimum_log_level = minimumLogLevel
        pass
    def __write(self, guildId: int, level: loglevel.LogLevel, method: str, message: str, stackTrace: str = None):
        print(f"[{level.name}] [{method}] [guild:{str(guildId)}] {message}")
        if stackTrace:
            print(stackTrace)
        if level >= self.minimum_log_level:
            self.db.insert_log(guildId=guildId, level=level, method=method, message=message, stackTrace=stackTrace)

    def debug(self, guildId: int, method: str, message: str, stackTrace: str = None):
        self.__write(guildId=guildId, level=loglevel.LogLevel.DEBUG, method=method, message=message, stackTrace=stackTrace)
    def info(self, guildId: int, method: str, message: str, stackTrace: str = None):
        self.__write(guildId=guildId, level=loglevel.LogLevel.INFO, method=method, message=message, stackTrace=stackTrace)
    def warn(self, guildId: int, method: str, message: str, stackTrace: str = None):
        self.__write(guildId=guildId, level=loglevel.LogLevel.WARNING, method=method, message=message, stackTrace=stackTrace)
    def error(self, guildId: int, method: str, message: str, stackTrace: str = None):
        self.__write(guildId=guildId, level=loglevel.LogLevel.ERROR, method=method, message=message, stackTrace=stackTrace)
    def fatal(self, guildId: int, method: str, message: str, stackTrace: str = None):
        self.__write(guildId=guildId, level=loglevel.LogLevel.FATAL, method=method, message=message, stackTrace=stackTrace)
