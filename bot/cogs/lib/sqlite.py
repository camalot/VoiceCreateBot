import sqlite3
import traceback
import json
import glob
from typing import final

from discord.ext.commands.converter import CategoryChannelConverter
from . import database
from . import settings
from . import utils
class SqliteDatabase(database.Database):
    def __init__(self):
        self.settings = settings.Settings()
        self.connection = None
        pass
    def open(self):
        self.connection = sqlite3.connect(self.settings.db_path)
        pass
    def close(self):
        try:
            if self.connection:
                self.connection.commit()
                self.connection.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)
        finally:
            self.connection = None
        pass
    def get_tracked_voice_channel_ids(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ?", (guildId,))
            items = [i[0] for i in c.fetchall()]
            return items
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_tracked_voice_channel_id_by_owner(self, guildId, ownerId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ? AND userID = ?", (guildId, ownerId,))
            channel_ids = [item for items in c.fetchall() for item in items]
            print(json.dumps(channel_ids))
            return channel_ids
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_guild_create_channels(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildId,))
            channel_ids = [item for clist in c.fetchall() for item in clist]
            return channel_ids
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)

    def get_text_channel_id(self, guildId, voiceChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT channelID FROM textChannel WHERE guildID = ? and voiceId = ?", (guildId, voiceChannelId))
            item = c.fetchone()
            if item:
                return item[0]
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_voice_channel_id_from_text_channel(self, guildId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceID FROM textChannel WHERE guildID = ? and channelID = ?", (guildId, textChannelId))
            item = c.fetchone()
            if item:
                return item[0]
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clean_tracked_channels(self, guildId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute('DELETE FROM voiceChannel WHERE guildID = ? and voiceId = ?', (guildId, voiceChannelId,))
            c.execute('DELETE FROM textChannel WHERE guildID = ? and channelID = ?', (guildId, textChannelId,))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        pass

    def get_channel_owner_id(self, guildId, channelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT userID FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildId, channelId,))
            item = c.fetchone()
            if item:
                return int(item[0])
            c.execute("SELECT userID FROM textChannel WHERE guildID = ? AND channelID = ?", (guildId, channelId,))
            item = c.fetchone()
            if item:
                return int(item[0])

            return None

        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_user_settings(self, guildId, userId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (userId, guildId,))
            row = c.fetchone()
            if row:
                result = settings.UserSettings(guildId=guildId, userId=userId, channelName=row[0], channelLimit=int(row[1]), bitrate=int(row[2]), defaultRole=row[3])
                return result
            print("NO USER SETTINGS FOUND")
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_guild_settings(self, guildId):
        pass
    def insert_or_update_guild_settings(self, guildId, prefix, defaultRole, adminRole):
        pass
    def insert_guild_settings(self, guildId, prefix, defaultRole, adminRole):
        pass
    def update_guild_settings(self, guildId, prefix, defaultRole, adminRole):
        pass
    def update_guild_create_channel_settings(self, guildId, createChannelId, categoryId, ownerId, useStage: bool):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            stageInt = 0
            if useStage:
                stageInt = 1

            c.execute("UPDATE guild SET ownerID = ?, voiceChannelID = ?, voiceCategoryID = ?, useStage = ? WHERE guildID = ? AND voiceChannelID = ?", (
                                ownerId, createChannelId, categoryId, stageInt, guildId, createChannelId))
            self.connection.commit()
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def insert_guild_create_channel_settings(self, guildId, createChannelId, categoryId, ownerId, useStage: bool):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            stageInt = 0
            if useStage:
                stageInt = 1
            c.execute("INSERT INTO guild VALUES (?, ?, ?, ?, ?)", (guildId, ownerId, createChannelId, categoryId, stageInt))
            self.connection.commit()
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False

    def get_guild_create_channel_settings(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT ownerID, voiceChannelID, voiceCategoryID, useStage FROM guild WHERE guildID = ?", (guildId,))
            rows = c.fetchall()
            if rows:
                result = settings.GuildCreateChannelSettings(guildId=guildId)
                for r in rows:
                    result.channels.append(settings.GuildCategoryChannel(ownerId=int(r[0]), categoryId=r[2], channelId=r[1], useStage=int(r[3])))
                return result
            print("NO GUILD SETTINGS FOUND")
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def delete_guild_create_channel(self, guildId, channelId, categoryId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("DELETE FROM guild WHERE guildID = ? AND voiceChannelID = ? AND voiceCategoryID = ?", (guildId, channelId, categoryId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
        pass
    def get_use_stage_on_create(self, guildId, channelId, categoryId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT useStage FROM guild WHERE guildID = ? AND voiceCategoryID = ? AND voiceChannelID = ?", (guildId, categoryId, channelId))
            create_channel = c.fetchone()
            if create_channel:
                return create_channel[0]
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)
    def set_guild_category_settings(self, guildId, categoryId, channelLimit, channelLocked, bitrate, defaultRole):
        try:
            if not self.connection:
                self.open()
            c = self.connection.cursor()
            cat_settings = self.get_guild_category_settings(guildId=guildId, categoryId=categoryId)
            if cat_settings:
                c.execute("UPDATE guildCategorySettings SET channelLimit = ?, channelLocked = ?, bitrate = ?, defaultRole = ? WHERE guildID = ? AND voiceCategoryID = ?", (channelLimit, channelLocked, bitrate, defaultRole, guildId, CategoryChannelConverter,))
            else:
                c.execute("INSERT INTO guildCategorySettings VALUES ( ?, ?, ?, ?, ?, ? )", (guildId, CategoryChannelConverter, channelLimit, channelLocked, bitrate, defaultRole,))
            self.connection.commit()
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def get_guild_category_settings(self, guildId, categoryId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildId, categoryId,))
            row = c.fetchone()
            if row:
                result = settings.GuildCategorySettings(guildId=guildId, categoryId=categoryId, channelLimit=int(row[0]), channelLocked=int(row[1]), bitrate=row[2], defaultRole=row[3])
                return result
            print("NO GUILD CATEGORY SETTINGS FOUND")
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        pass
    def update_user_channel_name(self, guildId, userId, channelName):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))

        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
        pass
    def update_user_limit(self, guildId, userId, limit: int = 0):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("UPDATE userSettings SET channelLimit = ? WHERE userID = ? AND guildID = ?", (limit, userId, guildId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
        pass
    def update_user_bitrate(self, guildId, userId, bitrate: int = 8):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("UPDATE userSettings SET bitrate = ? WHERE userID = ? AND guildID = ?", (bitrate, userId, guildId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
        pass
    def insert_user_settings(self, guildId, userId, channelName, channelLimit, bitrate: int, defaultRole: int):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?, ?)", (guildId, userId, channelName, channelLimit, bitrate, defaultRole))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
        pass
    def track_new_voice_channel(self, guildId, ownerId, voiceChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildId, ownerId, voiceChannelId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def track_new_channel_set(self, guildId, ownerId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildId, ownerId, voiceChannelId,))
            c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildId, ownerId, textChannelId, voiceChannelId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()

    def add_tracked_text_channel(self, guildId, ownerId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildId, ownerId, textChannelId, voiceChannelId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def delete_tracked_text_channel(self, guildId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("DELETE FROM textChannel WHERE guildID = ? AND voiceID = ? AND channelID = ?", (guildId, voiceChannelId, textChannelId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def get_tracked_channels_for_guild(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceID, userID FROM voiceChannel WHERE guildID = ?", (guildId,))
            voiceSets = c.fetchall()
            voice_channels = []
            for item in voiceSets:
                voice_channels.append(settings.TrackedVoiceChannel(guildId=guildId, ownerId=item[1], voiceChannelId=item[0]))
            c.execute("SELECT voiceID, channelID, userID FROM textChannel WHERE guildID = ?", (guildId,))
            textSets = c.fetchall()
            text_channels = []
            for item in textSets:
                text_channels.append(settings.TrackedTextChannel(guildId=guildId, ownerId=item[2], voiceChannelId=item[0], textChannelId=item[1]))
            tracked = settings.TrackedChannels(voiceChannels=voice_channels, textChannels=text_channels)
            return tracked
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_tracked_channel_owner(self, guildId, voiceChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT userID FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildId, voiceChannelId,))
            ownerSet = c.fetchone()
            if ownerSet:
                return int(ownerSet[0])
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def update_tracked_channel_owner(self, guildId, voiceChannelId, ownerId, newOwnerId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("UPDATE voiceChannel SET userID = ? WHERE guildId = ? AND voiceID = ? AND userID = ?", (newOwnerId, guildId, voiceChannelId, ownerId,))
            c.execute("UPDATE textChannel SET userID = ? WHERE guildId = ? AND voiceID = ? AND userID = ?", (newOwnerId, guildId, voiceChannelId, ownerId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def clean_guild_user_settings(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("DELETE FROM `userSettings` WHERE guildID = ?", (guildId, ))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def clean_user_settings(self, guildId, userId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("DELETE FROM `userSettings` WHERE guildID = ? AND userID = ?", (guildId, userId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def get_default_role(self, guildId, categoryId, userId):
        try:
            user_settings = self.get_user_settings(guildId=guildId, userId=userId)
            guild_category_settings = self.get_guild_category_settings(guildId=guildId, categoryId=categoryId)
            if user_settings:
                return user_settings.default_role
            elif guild_category_settings:
                return guild_category_settings.default_role
            else:
                return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def set_default_role_for_user(self, guildId, userId, defaultRole):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            user_settings = self.get_user_settings(guildId=guildId, userId=userId)
            if user_settings:
                c.execute("UPDATE userSettings SET defaultRole = ? WHERE WHERE guildID = ? and userId = ?", (defaultRole, guildId, userId))
                return True
            else:
                return False
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def set_default_role_for_category(self, guildId, categoryId, defaultRole):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            category_settings = self.get_guild_category_settings(guildId=guildId, categoryId=categoryId)
            if category_settings:
                c.execute("UPDATE guildCategorySettings SET defaultRole = ? WHERE WHERE guildID = ? and voiceCategoryID = ?", (defaultRole, guildId, categoryId))
                return True
            else:
                return False
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()

    def UPDATE_SCHEMA(self, newDBVersion: int):
        try:
            print(f"INITIALIZE SQLITE")
            if self.connection is None:
                self.open()
            dbversion = utils.get_scalar_result(self.connection, "PRAGMA user_version", 0)
            c = self.connection.cursor()
            print(f"LOADED SCHEMA VERSION: {dbversion}")
            print(f"CURRENT SCHEMA VERSION: {newDBVersion}")
            for x in range(0, newDBVersion+1):
                files = glob.glob(f"database/sql/{x:04d}.*.sql")
                for f in files:
                    if dbversion == 0 or dbversion < x:
                        print(f"Applying SQL: {f}")
                        file = open(f, mode='r')
                        contents = file.read()
                        c.executescript(contents)
                        self.connection.commit()
                        file.close()
                    else:
                        print(f"Skipping SQL: {f}")
            if dbversion < newDBVersion:
                print(f"Updating SCHEMA Version to {newDBVersion}")
                c.execute(f"PRAGMA user_version = {newDBVersion}")
                self.connection.commit()
            c.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            self.close()

    def get_all_from_guild_table(self):
        try:
            if not self.connection:
                self.open()
            c = self.connection.cursor()
            result = []
            rows = c.execute("SELECT guildID, ownerID, voiceChannelID, voiceCategoryID, useStage FROM guild")
            for r in rows:
                result.append({ "guildID": int(r[0]), "ownerID": int(r[1]), "voiceChannelID": int(r[2]), "voiceCategoryID": int(r[3]), "useStage": bool(r[4]) })
            return result
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_all_from_guild_category_settings_table(self):
        try:
            if not self.connection:
                self.open()
            c = self.connection.cursor()
            result = []
            rows = c.execute("SELECT guildID, voiceCategoryID, channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings")
            for r in rows:
                result.append({ "guildID": int(r[0]), "voiceCategoryID": int(r[1]), "channelLimit": int(r[2]), "channelLocked": bool(r[3]), "bitrate": int(r[4]), "defaultRole": str(r[5]) })
            return result

        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_all_from_user_settings_table(self):
        try:
            if not self.connection:
                self.open()
            c = self.connection.cursor()
            result = []
            rows = c.execute("SELECT guildID, userID, channelName, channelLimit, bitrate, defaultRole FROM userSettings")
            for r in rows:
                result.append({ "guildID": int(r[0]), "userID": int(r[1]), "channelName": str(r[2]), "channelLimit": int(r[3]), "bitrate": int(r[4]), "defaultRole": str(r[5]) })
            return result
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_all_from_text_channel_table(self):
        try:
            if not self.connection:
                self.open()
            c = self.connection.cursor()
            result = []
            rows = c.execute("SELECT guildID, userID, channelID, voiceID FROM textChannel")
            for r in rows:
                result.append({ "guildID": int(r[0]), "userID": int(r[1]), "channelID": int(r[2]), "voiceID": int(r[3]) })
            return result

        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_all_from_voice_channel_table(self):
        try:
            if not self.connection:
                self.open()
            c = self.connection.cursor()
            result = []
            rows = c.execute("SELECT guildID, userID, voiceID FROM voiceChannel")
            for r in rows:
                result.append({ "guildID": int(r[0]), "userID": int(r[1]), "voiceID": int(r[3]) })
            return result

        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
