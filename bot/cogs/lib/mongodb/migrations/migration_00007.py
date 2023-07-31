
# MIGRATE SETTINGS COLLECTION

from pymongo import MongoClient
from ..models.guild_settings import GuildSettingsV2
from ... import utils
from . import Migration
import inspect
import os

class Migration_00007(Migration):
    def __init__(self, connection):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.connection = connection
        self.log(f"{self._module}.{_method}", f"INITIALIZE MIGRATION 00007")
        pass
    def execute(self):
        _method = inspect.stack()[0][3]
        self.log(f"{self._module}.{_method}", f"EXECUTE MIGRATION 00007")
        # v7 migration start
        collections = self.connection.list_collection_names()
        if 'guild_settings' in collections:
            # if column "prefixes" exists, then we have already migrated
            if "prefixes" in self.connection['guild_settings'].find_one():
                self.log(f"{self._module}.{_method}", f"SKIPPING MIGRATION 00007: Already migrated")
                return

        # only migrate to this if the new settings collection doesnt exist
        if "guild_settings_v2" not in collections:
            # get all the guilds from the old collection
            guild_settings = self.connection['guild_settings'].find({})
            # loop through each guild
            for guild in guild_settings:
                # insert the guild into the new collection
                reformatted = GuildSettingsV2.from_v1_dict(guild)
                data = reformatted.__dict__
                data["timestamp"] = utils.get_timestamp()
                self.connection['guild_settings_v2'].insert_one(reformatted.__dict__)

            # rename the old collection
            self.connection['guild_settings'].rename('guild_settings_v1')
            # rename the new collection to the old collection name
            self.connection['guild_settings_v2'].rename('guild_settings')


        self.log(f"{self._module}.{_method}", f"COMPLETE MIGRATION 00007")
