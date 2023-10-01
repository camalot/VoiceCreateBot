import traceback
import os
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.mongodb.databasebase import DatabaseBase
from bot.cogs.lib.models.guild_settings import GuildSettings
from bot.cogs.lib.models.category_settings import GuildCategorySettings


class SettingsDatabase(DatabaseBase):
    def __init__(self):
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def get(self, guildId: int):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.guild_settings.find_one({"guild_id": str(guildId)})
            if c:
                return GuildSettings(
                    guildId=int(c['guild_id']),
                    prefixes=c['prefixes'],
                    defaultRole=int(c['default_role']),
                    adminRoles=[int(r) for r in c['admin_roles']],
                    language=c['language']
                )
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return None

    def set(self, settings: GuildSettings):
        try:
            if self.connection is None:
                self.open()
            payload = {
                "prefixes": settings.prefixes,
                "default_role": settings.default_role,
                "admin_roles": settings.admin_roles,
                "language": settings.language,
                "timestamp": utils.get_timestamp()
            }
            self.connection.guild_settings.update_one({"guild_id": str(settings.guild_id)}, { "$set": payload }, upsert=True)
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False

    def get_default_role(self, guildId: int, categoryId: typing.Optional[int], userId: typing.Optional[int]) -> typing.Optional[int]:
        if self.connection is None:
            self.open()

        if userId is not None: # check user settings
            user_settings = self.connection.user_settings.find_one({"guild_id": str(guildId), "user_id": str(userId)})
            if user_settings:
                if "default_role" in user_settings:
                    return int(user_settings['default_role'])
        if categoryId is not None:
            category_settings = self.connection.category_settings.find_one({"guild_id": str(guildId), "category_id": str(categoryId)})
            if category_settings:
                if "default_role" in category_settings:
                    return int(category_settings['default_role'])

        guild_settings = self.connection.guild_settings.find_one({"guild_id": str(guildId)})
        if guild_settings:
            if "default_role" in guild_settings:
                return int(guild_settings['default_role'])

        return None

    def delete_admin_role(self, guildId: int, roleId: int) -> bool:
        try:
            if self.connection is None:
                self.open()

            result = self.connection.guild_settings.update_one(
                {
                    "guild_id": str(guildId)
                },
                {
                    "$pull": {
                        "admin_roles": str(roleId)
                    },
                    "$set": {
                        "timestamp": utils.get_timestamp()
                    }
                }
            )

            if result.modified_count == 0:
                return False

            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False

    def add_admin_role(self, guildId: int, roleId: int) -> bool:
        try:
            if self.connection is None:
                self.open()

            result = self.connection.guild_settings.update_one(
                {
                    "guild_id": str(guildId)
                },
                {
                    "$addToSet": {
                        "admin_roles": str(roleId)
                    },
                    "$set": {
                        "timestamp": utils.get_timestamp()
                    }
                }
            )

            if result.modified_count == 0:
                return False

            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False

    def set_prefixes(self, guildId: int, prefixes: typing.List[str], append: bool = False):
        try:
            if self.connection is None:
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
            result = self.connection.guild_settings.update_one({"guild_id": str(guildId)}, { "$set": payload })
            if result.modified_count == 0:
                return False
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False

    def get_prefixes(self, guildId: int) -> typing.List[str]:
        if self.connection is None:
            self.open()
        gs = self.get(guildId=guildId)
        if not gs:
            return None
        print(gs.prefixes)
        return gs.prefixes

    def set_setting(self, guildId: int, key: str, value: typing.Any):
        if self.connection is None:
            self.open()
        gs = self.get(guildId=guildId)
        if not gs:
            return False
        payload = {
            key: value,
            "timestamp": utils.get_timestamp(),
        }
        self.connection.guild_settings.update_one({"guild_id": str(guildId)}, { "$set": payload })

    def get_guild_category_settings(self, guildId: int, categoryId: int) -> typing.Optional[GuildCategorySettings]:
        try:
            if self.connection is None:
                self.open()
            row = self.connection.category_settings.find_one({"guild_id": str(guildId), "voice_category_id": str(categoryId)})
            if row:
                result = GuildCategorySettings(
                    guildId=int(guildId),
                    categoryId=int(categoryId),
                    channelLimit=row['channel_limit'],
                    channelLocked=row['channel_locked'],
                    bitrate=row['bitrate'],
                    defaultRole=row['default_role']
                )
                return result
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    # def set_guild_settings_language(self, guildId: int, language: str):
    #     if self.connection is None:
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
    #         if self.connection is None:
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
    #         if self.connection is None:
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
    #         if self.connection is None:
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
