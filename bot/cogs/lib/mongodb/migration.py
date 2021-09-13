from bot.cogs.lib.mongodb import migrations
from .. import settings
from pymongo import MongoClient
import traceback
import json

class MongoMigration:

    def __init__(self):
        self.settings = settings.Settings()
        self.client = None
        self.connection = None
        print(f"INITIALIZE MIGRATOR")
        pass

    def run(self):
        self.open()
        try:
            pass
            # mod = __import__(".migrations.migration_00005", fromlist=['.'])
            # fp, path, desc = imp.find_module(".migrations")
            # mig = imp.load_module(".migrations.migration_00005.Migration_00005", fp, path, desc)
            # mod.Migration_00005().execute()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            # print ("module not found: " + ".migrations.migration_00005")
        self.close()
        pass

    def open(self):
        if not self.settings.db_url:
            raise ValueError("VCB_MONGODB_URL is not set")
        self.client = MongoClient(self.settings.db_url)
        self.connection = self.client.voicecreate
    def close(self):
        try:
            if self.client:
                self.client.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    
class MigrationAction:
    def __init__(self):
        pass
    def execute(self):
        pass