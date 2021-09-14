from bot.cogs.lib.mongodb import migrations
from .. import settings
from pymongo import MongoClient
import traceback
import json
from .migrations import *

class MongoMigration:

    def __init__(self, schemaVersion: int = 0):
        self.settings = settings.Settings()
        self.client = None
        self.connection = None
        self.schema_version = schemaVersion
        self.log("MongoMigration.__init__", "INITIALIZE MIGRATOR")
        pass

    def run(self):
        self.open()
        try:
            for mig in migrations.__all__:
                schemaIdx = int("".join(filter(str.isdigit, mig)))
                if schemaIdx not in range(0, self.schema_version+1):
                    self.log("migration.run", f"Skipping: {mig}: Out of range of current schema")
                    continue

                if self.schema_version == 0 or self.schema_version > schemaIdx:
                    module = getattr(migrations, mig)
                    class_ = getattr(module, f"{mig.title()}")
                    obj = class_(self.connection)
                    obj.execute()
                else:
                    self.log("migration.run", f"SKIPPING {mig.title()}: For Previous or Current Schema")
            pass
        except Exception as ex:
            self.log("migration.run", str(ex), traceback.format_exc())
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
           self.log("migration.close", str(ex), traceback.format_exc())

    def log(self, method: str, message: str, stackTrace: str = None):
        print(f"[DEBUG] [{method}] [guild:0] {message}")
        if stackTrace:
            print(stackTrace)

class MigrationAction:
    def __init__(self):
        pass
    def execute(self):
        pass
