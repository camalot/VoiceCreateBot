import traceback
import typing

from bot.cogs.lib.mongodb.database import Database


class LogsMongoDatabase(Database):
    def __init__(self):
        super().__init__()
        pass

    def clear_log(self, guildId):
        try:
            if self.connection is None:
                self.open()
            self.connection.logs.delete_many({ "guild_id": guildId })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
