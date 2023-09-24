import inspect
import os

from bot.cogs.lib.mongodb.migration import Migration


class Migration_00000(Migration):
    def __init__(self, connection):
        _method = inspect.stack()[0][3]
        super().__init__(connection)
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.log(f"{self._module}.{_method}", f"INITIALIZE MIGRATION 00000")
        pass
    def execute(self):
        _method = inspect.stack()[0][3]
        self.log(f"{self._module}.{_method}", f"EXECUTE MIGRATION 00000")
        # v0 migration start

        # disable the DB migration because this has already been done...
        # THIS COPIED FROM SQLITE DB -> MONGODB

        # print("NEEDS SQLITE -> MONGO MIGRATION")
        # sql3 = sqlite.SqliteDatabase()
        # gd = sql3.get_all_from_guild_table()
        # if gd:
        #     self.connection.create_channels.insert_many(gd)
        # gcsd = sql3.get_all_from_guild_category_settings_table()
        # if gcsd:
        #     self.connection.category_settings.insert_many(gcsd)
        # usd = sql3.get_all_from_user_settings_table()
        # if usd:
        #     self.connection.user_settings.insert_many(usd)
        # vcd = sql3.get_all_from_voice_channel_table()
        # if vcd:
        #     self.connection.voice_channels.insert_many(vcd)
        # tcd = sql3.get_all_from_text_channel_table()
        # if tcd:
        #     self.connection.text_channels.insert_many(tcd)
        self.log("Migration_00000.execute", f"COMPLETE MIGRATION 00000")
