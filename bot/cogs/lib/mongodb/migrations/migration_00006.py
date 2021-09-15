from pymongo import MongoClient
from . import Migration
class Migration_00006(Migration):
    def __init__(self, connection):
        self.connection = connection
        self.log("Migration_00006.__init__", f"INITIALIZE MIGRATION 00006")
        pass
    def execute(self):
        self.log("Migration_00006.execute", f"EXECUTE MIGRATION 00006")
        # v6 migration start
        collections = self.connection.list_collection_names()

        if "guild_settings" in collections:
            self.connection.guild_settings.update_many({}, { "$set": { "language": "en-us" } })

        self.log("Migration_00006.execute", f"COMPLETE MIGRATION 00006")
