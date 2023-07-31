from pymongo import MongoClient
import traceback
import json
import os
import typing

from .. import utils
from .models.guild_settings import GuildSettingsV2

class SettingsDatabase():
    def __init__(self):
        self.db_url = utils.dict_get(os.environ, "VCB_MONGODB_URL", default_value="")
        self.db_name = utils.dict_get(os.environ, "VCB_MONGODB_DBNAME", default_value = "voicecreate_v2")

        self.client: typing.Optional[MongoClient] = None
        self.connection: typing.Optional[typing.Any] = None
        pass

    def open(self):
        if not self.db_url:
            raise ValueError("VCB_MONGODB_URL is not set")
        if not self.db_name:
            raise ValueError("VCB_MONGODB_DBNAME is not set")
        self.client = MongoClient(self.db_url)
        self.connection = self.client[self.db_name]
    def close(self):
        try:
            if self.client:
                self.client.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get(self, guildId: int):
        try:
            if not self.connection:
                self.open()
            c = self.connection.guild_settings.find_one({"guild_id": guildId})
            if c:
                return GuildSettingsV2(
                    guildId=guildId,
                    prefixes=c['prefixes'],
                    defaultRole=c['default_role'],
                    adminRoles=c['admin_role'],
                    language=c['language']
                )
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return None

    def set(self, settings: GuildSettingsV2):
        try:
            if not self.connection:
                self.open()
            payload = {
                "prefixes": settings.prefixes,
                "default_role": settings.default_role,
                "admin_roles": settings.admin_roles,
                "language": settings.language,
                "timestamp": utils.get_timestamp()
            }
            self.connection.guild_settings.update_one({"guild_id": settings.guild_id}, { "$set": payload }, upsert=True)
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False


    def set_prefixes(self, guildId: int, prefixes: typing.List[str], append: bool = False):
        if not self.connection:
            self.open()
        gs = self.get(guildId=guildId)
        if not gs:
            return False

        if append:
            prefixes = gs.prefixes + prefixes

        payload = {
            "prefixes": prefixes,
            "timestamp": utils.get_timestamp(),
        }
        self.connection.guild_settings.update_one({"guild_id": guildId}, { "$set": payload })

    def set_setting(self, guildId: int, key: str, value: typing.Any):
        if not self.connection:
            self.open()
        gs = self.get(guildId=guildId)
        if not gs:
            return False
        payload = {
            key: value,
            "timestamp": utils.get_timestamp(),
        }
        self.connection.guild_settings.update_one({"guild_id": guildId}, { "$set": payload })

    # def set_guild_settings_language(self, guildId: int, language: str):
    #     if not self.connection:
    #         self.open()
    #     gs = self.get_guild_settings(guildId=guildId)
    #     if not gs:
    #         return False
    #     payload = {
    #         "language": language,
    #         "timestamp": utils.get_timestamp()
    #     }
    #     self.connection.guild_settings.update_one({"guild_id": guildId}, { "$set": payload })

    # def insert_or_update_guild_settings(self, guildId: int, prefix: str, defaultRole: int, adminRole: int, language: str):
    #     try:
    #         if not self.connection:
    #             self.open()
    #         gs = self.get_guild_settings(guildId=guildId)
    #         if gs:
    #             return self.update_guild_settings(guildId=gs.guild_id, prefix=prefix, defaultRole=defaultRole, adminRole=adminRole, language=language)
    #         else:
    #             return self.insert_guild_settings(guildId=guildId, prefix=prefix, defaultRole=defaultRole, adminRole=adminRole, language=language)
    #     except Exception as ex:
    #         print(ex)
    #         traceback.print_exc(ex)
    #         return False
    # def insert_guild_settings(self, guildId: int, prefix: str, defaultRole: int, adminRole: int, language: str):
    #     try:
    #         if not self.connection:
    #             self.open()
    #         payload = {
    #             "guild_id": guildId,
    #             "prefix": prefix,
    #             "default_role": defaultRole,
    #             "admin_role": adminRole,
    #             "language": language,
    #             "timestamp": utils.get_timestamp()
    #         }
    #         self.connection.guild_settings.insert_one(payload)
    #         return True
    #     except Exception as ex:
    #         print(ex)
    #         traceback.print_exc()
    #         return False
    # def update_guild_settings(self, guildId: int, prefix: str, defaultRole: int, adminRole: int, language: str):
    #     try:
    #         if not self.connection:
    #             self.open()
    #         payload = {
    #             "prefix": prefix,
    #             "default_role": defaultRole,
    #             "admin_role": adminRole,
    #             "language": language,
    #             "timestamp": utils.get_timestamp()
    #         }
    #         self.connection.guild_settings.update_one({"guild_id": guildId}, { "$set": payload })
    #         return True
    #     except Exception as ex:
    #         print(ex)
    #         traceback.print_exc()
    #         return False
