import traceback
import typing

from bot.cogs.lib.mongodb.database import Database

class ExporterMongoDatabase(Database):

    def __init__(self):
        super().__init__()
        pass

    def get_guilds(self) -> typing.Optional[typing.Iterable[dict[str, typing.Any]]]:
        """Get all guilds"""
        try:
            if self.connection is None:
                self.open()
            return self.connection.guilds.find()
        except Exception as e:
            print(e)
            traceback.print_exc()
            # self.log.error(traceback.format_exc())
            return None

    def get_user_settings_count(self) -> typing.Optional[typing.Iterable[dict[str, typing.Any]]]:
        """Get all user settings"""
        try:
            if self.connection is None:
                self.open()
            return self.connection.user_settings.aggregate([
                {
                    "$group": {
                        "_id": "$guild_id",
                        "total": {"$sum": 1}
                    }
                }
            ])
        except Exception as e:
            print(e)
            traceback.print_exc()
            # self.log.error(traceback.format_exc())
            return None
