
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
        super().__init__(connection)
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.log(f"{self._module}.{_method}", f"INITIALIZE MIGRATION 00007")
        pass
    def execute(self):
        _method = inspect.stack()[0][3]
        self.log(f"{self._module}.{_method}", f"EXECUTE MIGRATION 00007")
        # v7 migration start
        collections = self.connection.list_collection_names()

        self._run_guild_settings(collections)

        self._run_user_settings(collections)

        self._run_create_channels(collections)

        self._run_category_settings(collections)

        self.log(f"{self._module}.{_method}", f"COMPLETE MIGRATION 00007")

    def _run_category_settings(self, collections) -> bool:
        _method = inspect.stack()[0][3]
        if "category_settings" in collections:
            if "guild_id" in self.connection['category_settings'].find_one():
                self.log(f"{self._module}.{_method}", f"SKIPPING CATEGORY SETTINGS: Already migrated")
                return True

            self.log(f"{self._module}.{_method}", f"MIGRATING CATEGORY SETTINGS")
            self.connection['category_settings'].update_many({}, {
                "$rename": {
                    "guildID": "guild_id",
                    "voiceCategoryID": "voice_category_id",
                    "defaultRole": "default_role",
                    "channelLimit": "channel_limit",
                    "channelLocked": "channel_locked",
                },
                "$set": {
                    "allow_soundboard": False,
                    "auto_name": True,
                    "auto_game": False,
                },
            })
            for x in self.connection['category_settings'].find({}):
                self.connection['category_settings'].update_one(
                    {"_id": x["_id"]},
                    {
                        "$set": {
                            "guild_id": str(int(x["guild_id"])),
                            "voice_category_id": str(int(x["voice_category_id"])),
                            "default_role": str(int(x["default_role"])),
                            "timestamp": utils.get_timestamp(),
                        }
                    }
                )

        return True

    def _run_create_channels(self, collections) -> bool:
        _method = inspect.stack()[0][3]
        if "create_channels" in collections:
            if "guild_id" in self.connection['create_channels'].find_one():
                self.log(f"{self._module}.{_method}", f"SKIPPING CREATE CHANNELS: Already migrated")
                return True
            self.log(f"{self._module}.{_method}", f"MIGRATING CREATE CHANNELS")

            self.connection['create_channels'].update_many({}, {
                "$rename": {
                    "guildID": "guild_id",
                    "ownerID": "owner_id",
                    "voiceChannelID": "voice_channel_id",
                    "voiceCategoryID": "voice_category_id",
                    "useStage": "use_stage",
                },
            })
            for x in self.connection['create_channels'].find({}):
                self.connection['create_channels'].update_one(
                    {"_id": x["_id"]},
                    {
                        "$set": {
                            "guild_id": str(int(x["guild_id"])),
                            "owner_id": str(int(x["owner_id"])),
                            "voice_channel_id": str(int(x["voice_channel_id"])),
                            "voice_category_id": str(int(x["voice_category_id"])),
                            "timestamp": utils.get_timestamp(),
                        }
                    }
                )
        return True
    def _run_user_settings(self, collections) -> bool:
        _method = inspect.stack()[0][3]
        if "user_settings" in collections:
            # check if the user_settings collection has the new "guild_id" column
            if "guild_id" in self.connection['user_settings'].find_one():
                self.log(f"{self._module}.{_method}", f"SKIPPING USER SETTINGS: Already migrated")
                return True

            self.log(f"{self._module}.{_method}", f"MIGRATING USER SETTINGS")
            self.connection['user_settings'].update_many({}, {
                "$rename": {
                    "guildID": "guild_id",
                    "userID": "user_id",
                    "defaultRole": "default_role",
                    "channelName": "channel_name",
                    "channelLimit": "channel_limit",
                },
                # add the column "allow_soundboard" and "auto_name" if they do not exist
                "$set": {
                    "allow_soundboard": False,
                    "auto_name": True,
                    "channel_locked": False,
                }
            })
            for x in self.connection['user_settings'].find({}):
                self.connection['user_settings'].update_one(
                    {"_id": x["_id"]},
                    {
                        "$set": {
                            "guild_id": str(int(x["guild_id"])),
                            "user_id": str(int(x["user_id"])),
                            "default_role": str(int(x["default_role"])),
                            "timestamp": utils.get_timestamp(),
                        }
                    }
                )
        return True

    def _run_guild_settings(self, collections) -> bool:
        _method = inspect.stack()[0][3]
        # only migrate to this if the new settings collection doesnt exist
        if 'guild_settings' in collections:
            if 'guild_settings_v1' in collections:
                return True
            if "prefixes" in self.connection['guild_settings'].find_one():
                self.log(f"{self._module}.{_method}", f"SKIPPING GUILD SETTINGS: Already migrated")
                return True
            # get all the guilds from the old collection
            guild_settings = self.connection['guild_settings'].find({})

            self.log(f"{self._module}.{_method}", f"MIGRATING GUILD SETTINGS")
            # loop through each guild
            for guild in guild_settings:
                # insert the guild into the new collection
                reformatted = GuildSettingsV2.from_v1_dict(guild)
                if reformatted is None:
                    raise Exception("Failed to migrate guild settings")

                # convert '.' prefix to defaults
                # find the '.' prefix
                if '.' in reformatted.prefixes:
                    # remove it
                    reformatted.prefixes.remove('.')
                    # add the default prefixes
                    reformatted.prefixes.extend(['.vcb ', '!vcb ', '?vcb ', ".voice ", "!voice ", "?voice "])

                data = reformatted.__dict__
                data["timestamp"] = utils.get_timestamp()
                self.connection['guild_settings_v2'].insert_one(reformatted.__dict__)

            # rename the old collection
            self.connection['guild_settings'].rename('guild_settings_v1')
            # rename the new collection to the old collection name
            self.connection['guild_settings_v2'].rename('guild_settings')

            return True
        return True
