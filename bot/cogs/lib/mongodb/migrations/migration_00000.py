from pymongo import MongoClient
from . import Migration
from ... import sqlite

class Migration_00000(Migration):
    def __init__(self, connection):
        self.connection = connection
        self.log("Migration_00000.__init__", f"INITIALIZE MIGRATION 00000")
        pass
    def execute(self):
        self.log("Migration_00000.execute", f"EXECUTE MIGRATION 00000")
        # v0 migration start

        # disable the migration because this has already been done...
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
