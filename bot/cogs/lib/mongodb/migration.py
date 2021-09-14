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
            for migration_index in range(0, self.schema_version + 1):
                mig_name = f"migration_{migration_index:05d}"
                if mig_name in migrations.__all__:
                    if self.schema_version == 0 or self.schema_version < migration_index:
                        self.log("migration.run", f"Schema Version: {self.schema_version}")
                        self.log("migration.run", f"Migration Index: {migration_index}")
                        module = getattr(migrations, mig_name)
                        class_ = getattr(module, f"{mig_name.title()}")
                        obj = class_(self.connection)
                        obj.execute()
                    else:
                        self.log("migration.run", f"SKIPPING {mig_name.title()}: For Previous or Current Schema")
                else:
                    self.log("migration.run", f"NO MIGRATION FOR {mig_name}")
        except Exception as ex:
            self.log("migration.run", str(ex), traceback.format_exc())
        self.close()

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
