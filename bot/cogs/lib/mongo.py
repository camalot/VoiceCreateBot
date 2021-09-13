from pymongo import MongoClient
import traceback
import json

# from discord.ext.commands.converter import CategoryChannelConverter
from . import database
from . import settings
from . import utils
from . import sqlite

class MongoDatabase(database.Database):
    def __init__(self):
        self.settings = settings.Settings()
        self.client = None
        self.connection = None
        pass

    def RESET_MIGRATION(self):
        try:
            if not self.connection:
                self.open()
            print("RESET MIGRATION STATUS")
            self.connection.create_channels.delete_many({})
            self.connection.category_settings.delete_many({})
            self.connection.user_settings.delete_many({})
            self.connection.text_channels.delete_many({})
            self.connection.voice_channels.delete_many({})
            self.connection.migration.delete_many({})
            print("ALL DATA PURGED")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def UPDATE_SCHEMA(self, newDBVersion: int):
        print(f"[mongo.UPDATE_SCHEMA] INITIALIZE MONGO")
        try:
            # check if migrated
            # if not, open sqlitedb and migate the data
            if not self.connection:
                self.open()
            db_version = self.connection.migration.find_one({"user_version": newDBVersion})
            if not db_version:
                # need to migrate

                # v5 migration start
                if self.connection['guild']:
                    self.connection['guild'].rename("create_channels")
                if self.connection['guildCategorySettings']:
                    self.connection['guildCategorySettings'].rename("category_settings")
                if self.connection['userSettings']:
                    self.connection['userSettings'].rename("user_settings")
                if self.connection['textChannel']:
                    self.connection['textChannel'].rename("text_channels")
                if self.connection['voiceChannel']:
                    self.connection['voiceChannel'].rename("voice_channels")
                # v5 migration end

                pass
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
                self.connection.migration.delete_many({})
                self.connection.migration.insert_one({"user_version": newDBVersion, "timestamp": utils.get_timestamp()})
                print(f"[mongo.UPDATE_SCHEMA] DATABASE MIGRATION VERSION {str(newDBVersion)}")

            else:
                print(f"[mongo.UPDATE_SCHEMA] DATABASE MIGRATION VERSION {str(newDBVersion)}")

            # setup missing guild category settings...
            guild_channels = self.connection.create_channels.find({}, { "guildID": 1, "voiceChannelID": 1, "voiceCategoryID": 1 })
            for g in guild_channels:
                gcs = self.get_guild_category_settings(guildId=g['guildID'], categoryId=g['voiceCategoryID'])
                if not gcs:
                    print(f"[UPDATE_SCHEMA] Inserting Default Category Settings for guild: {g['guildID']} category: {g['voiceCategoryID']}")
                    guild_setting = self.get_guild_settings(g['guildID'])
                    if guild_setting:
                        self.set_guild_category_settings(guildId=g['guildID'], categoryId=g['voiceCategoryID'], channelLimit=0, channelLocked=False, bitrate=64, defaultRole=guild_setting.default_role)
                    else:
                        self.set_guild_category_settings(guildId=g['guildID'], categoryId=g['voiceCategoryID'], channelLimit=0, channelLocked=False, bitrate=64, defaultRole="@everyone")

        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
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
            print(ex)
            traceback.print_exc()
    def get_tracked_voice_channel_ids(self, guildId):
        try:
            if self.connection is None:
                self.open()
            cursor = self.connection.voice_channels.find({"guildID": guildId}, { "voiceID": 1 })
            items = [ i['voiceID'] for i in cursor ]
            return items
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_text_channel_id(self, guildId, voiceChannelId):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.text_channels.find_one({"guildID": guildId, "voiceID": voiceChannelId})
            if result:
                return result['channelID']
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_voice_channel_id_from_text_channel(self, guildId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.text_channels.find_one({"guildId": guildId, "channelID": textChannelId})
            if result:
                return result['voiceID']
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clean_tracked_channels(self, guildId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            tracked_voice = self.connection.voice_channels.find_one({ "guildID": guildId, "voiceID": voiceChannelId})
            if tracked_voice:
                tracked_text = self.connection.text_channels.find_one({"guildID": guildId, "voiceID": voiceChannelId, "channelID": textChannelId })
                text_channel_id = None
                if tracked_text:
                    text_channel_id = tracked_text['channelID']
                payload = {
                    "guild_id": guildId,
                    "user_id": tracked_voice['userID'],
                    "text_channel_id": text_channel_id,
                    "voice_channel_id": tracked_voice['voiceID'],
                    "timestamp": utils.get_timestamp()
                }
                self.connection.tracked_channels_history.insert_one(payload)
            self.connection.voice_channels.delete_one({"guildID": guildId, "voiceID": voiceChannelId})
            self.connection.text_channels.delete_one({"guildID": guildId, "channelID": textChannelId})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clean_guild_user_settings(self, guildId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("DELETE FROM `userSettings` WHERE guildID = ?", (guildId, ))
            self.connection.user_settings.delete_many({"guildID": guildId})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clean_user_settings(self, guildId, userId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("DELETE FROM `userSettings` WHERE guildID = ? AND userID = ?", (guildId, userId,))
            self.connection.user_settings.delete_many({"guildID": guildId, "userID": userId})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_tracked_voice_channel_id_by_owner(self, guildId, ownerId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ? AND userID = ?", (guildId, ownerId,))
            items = self.connection.voice_channels.find({"guildID": guildId, "userID": ownerId}, {"voiceID": 1})
            channel_ids = [item['voiceID'] for item in items]
            return channel_ids
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_channel_owner_id(self, guildId, channelId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT userID FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildId, channelId,))
            # c.execute("SELECT userID FROM textChannel WHERE guildID = ? AND channelID = ?", (guildId, channelId,))
            item = self.connection.voice_channels.find_one({"guildID": guildId, "voiceID": channelId}, {"userID": 1})
            if item:
                return int(item['userID'])
            item = self.connection.text_channels.find_one({"guildID": guildId, "channelID": channelId}, {"userID": 1})
            if item:
                return int(item['userID'])
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_user_settings(self, guildId, userId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (userId, guildId,))
            r = self.connection.user_settings.find_one({"guildID": guildId, "userID": userId})
            if r:
                return settings.UserSettings(guildId=guildId, userId=userId, channelName=r['channelName'], channelLimit=int(r['channelLimit']), bitrate=int(r['bitrate']), defaultRole=r['defaultRole'], autoGame=r['auto_game'])
            else:
                return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_guild_create_channel_settings(self, guildId):
        try:
            if self.connection is None:
                self.open()
            rows = self.connection.create_channels.find({"guildID": guildId})
            if rows:
                result = settings.GuildCreateChannelSettings(guildId=guildId)
                for r in rows:
                    result.channels.append(settings.GuildCategoryChannel(ownerId=(r['ownerID']), categoryId=int(r['voiceCategoryID']), channelId=int(r['voiceChannelID']), useStage=r['useStage']))
                return result
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def delete_guild_create_channel(self, guildId, channelId, categoryId):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("DELETE FROM guild WHERE guildID = ? AND voiceChannelID = ? AND voiceCategoryID = ?", (guildId, channelId, categoryId,))
            self.connection.create_channels.delete_many({"guildID": guildId, "voiceChannelID": channelId, "voiceCategoryID": categoryId})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        pass
    def update_guild_create_channel_settings(self, guildId, createChannelId, categoryId, ownerId, useStage: bool):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            self.connection.create_channels.find_one_and_update({"guildID": guildId, "voiceChannelID": createChannelId}, { "$set": { "ownerID": ownerId, "voiceCategoryID": categoryId, "useStage": useStage } })
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def insert_guild_create_channel_settings(self, guildId: int, createChannelId: int, categoryId: int, ownerId: int, useStage: bool):
        if self.connection is None:
            self.open()

        payload = {
            "guildID": guildId,
            "ownerID": ownerId,
            "voiceChannelID": createChannelId,
            "voiceCategoryID": categoryId,
            "useStage": useStage,
            "timestamp": utils.get_timestamp()
        }
        result = self.connection.create_channels.insert_one(payload)
        # c.execute("INSERT INTO guild VALUES (?, ?, ?, ?, ?)", (guildId, ownerId, createChannelId, categoryId, stageInt))
        return result is not None
    def get_guild_settings(self, guildId):
        try:
            if not self.connection:
                self.open()
            c = self.connection.guild_settings.find_one({"guild_id": guildId})
            if c:
                return settings.GuildSettings(guildId=guildId, prefix=c['prefix'], defaultRole=c['default_role'], adminRole=c['admin_role'])
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)
            return None
    def set_guild_settings_prefix(self, guildId, prefix: str):
        if not self.connection:
            self.open()
        gs = self.get_guild_settings(guildId=guildId)
        if not gs:
            return False
        payload = {
            "prefix": prefix
        }
        self.connection.guild_settings.update_one({"guild_id": guildId}, { "$set": payload })
    def insert_or_update_guild_settings(self, guildId, prefix, defaultRole, adminRole):
        try:
            if not self.connection:
                self.open()
            gs = self.get_guild_settings(guildId=guildId)
            if gs:
                return self.update_guild_settings(guildId=gs.guild_id, prefix=prefix, defaultRole=defaultRole, adminRole=adminRole)
            else:
                return self.insert_guild_settings(guildId=guildId, prefix=prefix, defaultRole=defaultRole, adminRole=adminRole)
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)
            return False
    def insert_guild_settings(self, guildId, prefix, defaultRole, adminRole):
        try:
            if not self.connection:
                self.open()
            payload = {
                "guild_id": guildId,
                "prefix": prefix,
                "default_role": defaultRole,
                "admin_role": adminRole,
                "timestamp": utils.get_timestamp()
            }
            self.connection.guild_settings.insert_one(payload)
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def update_guild_settings(self, guildId, prefix, defaultRole, adminRole):
        try:
            if not self.connection:
                self.open()
            payload = {
                "prefix": prefix,
                "default_role": defaultRole,
                "admin_role": adminRole,
                "timestamp": utils.get_timestamp()
            }
            self.connection.guild_settings.update_one({"guild_id": guildId}, { "$set": payload })
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def set_guild_category_settings(self, guildId: int, categoryId: int, channelLimit: int, channelLocked: bool, bitrate: int, defaultRole: int):
        try:
            if not self.connection:
                self.open()
            # c = self.connection.cursor()
            cat_settings = self.get_guild_category_settings(guildId=guildId, categoryId=categoryId)
            if cat_settings:
                payload = { "channelLimit": channelLimit, "channelLocked": channelLocked, "bitrate": bitrate, "defaultRole": defaultRole }
                self.connection.category_settings.find_one_and_update({"guildID": guildId, "voiceCategoryID": categoryId}, { "$set": payload })
                # c.execute("UPDATE guildCategorySettings SET channelLimit = ?, channelLocked = ?, bitrate = ?, defaultRole = ? WHERE guildID = ? AND voiceCategoryID = ?", (channelLimit, channelLocked, bitrate, defaultRole, guildId, CategoryChannelConverter,))
            else:
                # c.execute("INSERT INTO guildCategorySettings VALUES ( ?, ?, ?, ?, ?, ? )", (guildId, CategoryChannelConverter, channelLimit, channelLocked, bitrate, defaultRole,))
                payload = {
                    "guildID": guildId,
                    "voiceCategoryID": categoryId,
                    "channelLimit": channelLimit,
                    "channelLocked": channelLocked,
                    "bitrate": bitrate,
                    "defaultRole": defaultRole,
                    "timestamp": utils.get_timestamp()
                }
                self.connection.category_settings.insert_one(payload)
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def get_guild_category_settings(self, guildId, categoryId):
        try:
            if self.connection is None:
                self.open()
            row = self.connection.category_settings.find_one({ "guildID": guildId, "voiceCategoryID": categoryId})
            if row:
                result = settings.GuildCategorySettings(guildId=guildId, categoryId=categoryId, channelLimit=row['channelLimit'], channelLocked=row['channelLocked'], bitrate=row['bitrate'], defaultRole=row['defaultRole'])
                return result
            # c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildId, categoryId,))
            print(f"NO CATEGORY SETTINGS FOUND: {guildId}:{categoryId}")
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def update_user_channel_name(self, guildId, userId, channelName):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
            self.connection.user_settings.find_one_and_update({ "guildID": guildId, "userID": userId }, { "$set": { "channelName": channelName }})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def update_user_limit(self, guildId, userId, limit: int = 0):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
            self.connection.user_settings.find_one_and_update({ "guildID": guildId, "userID": userId }, { "$set": { "channelLimit": limit }})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def update_user_bitrate(self, guildId, userId, bitrate: int = 8):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
            self.connection.user_settings.find_one_and_update({ "guildID": guildId, "userID": userId }, { "$set": { "bitrate": bitrate }})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def insert_user_settings(self, guildId, userId, channelName, channelLimit, bitrate: int, defaultRole: int, autoGame: bool = False):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
            payload = {
                "guildID": guildId,
                "userID": userId,
                "channelName": channelName,
                "channelLimit": channelLimit,
                "bitrate": bitrate,
                "defaultRole": defaultRole,
                "auto_game": autoGame,
                "timestamp": utils.get_timestamp()
            }
            self.connection.user_settings.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def set_user_settings_auto_game(self, guildId: int, userId: int, autoGame: bool):
        if self.connection is None:
            self.open()
        existing = self.get_user_settings(guildId=guildId, userId=userId)
        if existing:
            self.connection.user_settings.update_one({"guildID": guildId, "userID": userId}, { "$set": { "auto_game": autoGame }})
    def get_guild_create_channels(self, guildId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildId,))
            cursor = self.connection.create_channels.find({"guildID": guildId}, { "voiceChannelID": 1 })
            result = []
            for c in cursor:
                result.append(c['voiceChannelID'])
            return result
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)
    def get_use_stage_on_create(self, guildId, channelId, categoryId):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.create_channels.find_one({ "guildID": guildId, "voiceCategoryID": categoryId, "voiceChannelID": channelId }, { "useStage": 1 })
            if result:
                return result['useStage']
            return None
            # c.execute("SELECT useStage FROM guild WHERE guildID = ? AND voiceCategoryID = ? AND voiceChannelID = ?", (guildId, categoryId, channelId))
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)
    def add_tracked_text_channel(self, guildId, ownerId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildId, ownerId, textChannelId, voiceChannelId,))
            payload = {
                "guildID": guildId,
                "userID": ownerId,
                "channelID": textChannelId,
                "voiceID": voiceChannelId
            }
            self.connection.text_channels.insert_one(payload)
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def delete_tracked_text_channel(self, guildId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("DELETE FROM textChannel WHERE guildID = ? AND voiceID = ? AND channelID = ?", (guildId, voiceChannelId, textChannelId,))
            # tracked = self.connection.tracked_channels.find_one({"textChannel": { "id": textChannelId }, "voiceChannel": { "id" : voiceChannelId }})
            # tracked_text = self.connection.text_channels.find_one({"channelID": textChannelId, "guildID": guildId, "voiceID": voiceChannelId })
            # tracked_voice = self.connection.voice_channels.fine_one({ "voiceID": voiceChannelId, "guildID": guildId })
            # tt_payload = None
            # tv_payload = None
            # if tracked_text:
            #     tt_payload = {
            #         "id": tracked_text['channelID'],
            #         "user_id": tracked_text['userID']
            #     }
            # if tracked_voice:
            #     tv_payload = {
            #         "id": tracked_voice['voiceID']
            #     }
            # payload = {
            #     "guild_id": guildId,
            #     "text_channel": tt_payload,
            #     "voice_channel": tv_payload
            # }

            tracked = self.connection.text_channels.find_one({ "guildID": guildId, "voiceID": voiceChannelId, "channelID": textChannelId })
            if tracked:
                payload = {
                    "guild_id": guildId,
                    "user_id": tracked['userID'],
                    "text_channel_id": tracked['channelID'],
                    "voice_channel_id": tracked['voiceID'],
                    "timestamp": utils.get_timestamp()
                }
                self.connection.tracked_channels_history.insert_one(payload)
            self.connection.text_channels.delete_one({ "guildID": guildId, "voiceID": voiceChannelId, "channelID": textChannelId })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def track_new_voice_channel(self, guildId, ownerId, voiceChannelId):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildId, ownerId, voiceChannelId,))
            payload = {
                "guildID": guildId,
                "userID": ownerId,
                "voiceID": voiceChannelId
            }
            self.connection.voice_channels.insert_one(payload)
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def track_new_channel_set(self, guildId, ownerId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildId, ownerId, voiceChannelId,))
            # c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildId, ownerId, textChannelId, voiceChannelId,))
            result = self.track_new_voice_channel(guildId=guildId, ownerId=ownerId, voiceChannelId=voiceChannelId)
            if result:
                result = self.add_tracked_text_channel(guildId=guildId, ownerId=ownerId, voiceChannelId=voiceChannelId, textChannelId=textChannelId)
            return result
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def get_tracked_channels_for_guild(self, guildId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT voiceID, userID FROM voiceChannel WHERE guildID = ?", (guildId,))
            # c.execute("SELECT voiceID, channelID, userID FROM textChannel WHERE guildID = ?", (guildId,))
            voice_channels = []
            text_channels = []
            data = self.connection.voice_channels.find({"guildID": guildId}, { "voiceID": 1, "userID": 1 })
            for item in data:
                voice_channels.append(settings.TrackedVoiceChannel(guildId=guildId, ownerId=item['userID'], voiceChannelId=item['voiceID']))
            data = self.connection.text_channels.find({"guildID": guildId}, {"voiceID": 1, "channelID": 1, "userID": 1})
            for item in data:
                text_channels.append(settings.TrackedTextChannel(guildId=guildId, ownerId=item['userID'], voiceChannelId=item['voiceID'], textChannelId=item['channelID']))
            tracked = settings.TrackedChannels(voiceChannels=voice_channels, textChannels=text_channels)
            return tracked
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_tracked_channel_owner(self, guildId, voiceChannelId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT userID FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildId, voiceChannelId,))
            owner = self.connection.voice_channels.find_one({"guildID": guildId, "voiceID": voiceChannelId}, { "userID": 1 })
            if owner:
                return owner['userID']
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def update_tracked_channel_owner(self, guildId, voiceChannelId, ownerId, newOwnerId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("UPDATE voiceChannel SET userID = ? WHERE guildId = ? AND voiceID = ? AND userID = ?", (newOwnerId, guildId, voiceChannelId, ownerId,))
            # c.execute("UPDATE textChannel SET userID = ? WHERE guildId = ? AND voiceID = ? AND userID = ?", (newOwnerId, guildId, voiceChannelId, ownerId,))
            self.connection.voice_channels.update_one({"guildID": guildId, "voiceID": voiceChannelId, "userID": ownerId}, {"$set": { "userID": newOwnerId }})
            self.connection.text_channels.update_one({"guildID": guildId, "voiceID": voiceChannelId, "userID": ownerId}, {"$set": { "userID": newOwnerId }})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clean_guild_user_settings(self, guildId):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("DELETE FROM `userSettings` WHERE guildID = ?", (guildId, ))
            self.connection.user_settings.delete_many({"guildID": guildId})
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def get_default_role(self, guildId, categoryId, userId):
        try:
            guild_settings = self.get_guild_settings(guildId=guildId)
            user_settings = self.get_user_settings(guildId=guildId, userId=userId)
            guild_category_settings = self.get_guild_category_settings(guildId=guildId, categoryId=categoryId)
            if user_settings:
                return user_settings.default_role
            elif guild_category_settings:
                return guild_category_settings.default_role
            elif guild_settings:
                return guild_settings.default_role
            else:
                return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def set_default_role_for_user(self, guildId, userId, defaultRole):  # update to use role id
        try:
            if self.connection is None:
                self.open()
            user_settings = self.get_user_settings(guildId=guildId, userId=userId)
            if user_settings:
                # c.execute("UPDATE userSettings SET defaultRole = ? WHERE WHERE guildID = ? and userId = ?", (defaultRole, guildId, userId))
                self.connection.user_settings.update_one({ "guildID": guildId, "userID": userId }, { "$set": { "defaultRole": defaultRole }})
                return True
            else:
                return False
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def set_default_role_for_category(self, guildId, categoryId, defaultRole):
        try:
            if self.connection is None:
                self.open()
            category_settings = self.get_guild_category_settings(guildId=guildId, categoryId=categoryId)
            if category_settings:
                self.connection.category_settings.update_many({ "guildID": guildId, "voiceCategoryID": categoryId}, { "$set": { "defaultRole": defaultRole }})
                return True
            return False
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def insert_log(self, guildId: int, level: str, method: str, message: str, stackTrace: str = None):
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": guildId,
                "timestamp": utils.get_timestamp(),
                "level": level.name,
                "method": method,
                "message": message,
                "stack_trace": stackTrace
            }
            self.connection.logs.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clear_log(self, guildId):
        try:
            if self.connection is None:
                self.open()
            self.connection.logs.delete_many({ "guild_id": guildId })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_all_guild_settings(self):
        if self.connection is None:
            self.open()
        c = self.connection.guild_settings.find()
        result = []
        for g in c:
            result.append(settings.GuildSettings(g['guild_id'], g['prefix'], g['default_role'], g['admin_role']))
        return result
    def get_all_from_guild_table(self):
        pass
    def get_all_from_guild_category_settings_table(self):
        pass
    def get_all_from_user_settings_table(self):
        pass
    def get_all_from_text_channel_table(self):
        pass
    def get_all_from_voice_channel_table(self):
        pass
