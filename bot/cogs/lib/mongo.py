
from pymongo import MongoClient
import traceback
import json

from discord.ext.commands.converter import CategoryChannelConverter
from . import database
from . import settings
from . import utils

class MongoDatabase(database.Database):
    def __init__(self):
        self.settings = settings.Settings()
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
    def get_tracked_voice_channel_ids(self, guildId):
        try:
            if self.connection is None:
                self.open()
            items = self.connection.voiceChannel.find({"guildID": guildId})
            return items
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_text_channel_id(self, guildId, voiceChannelId):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.textChannel.find_one({"guildId": guildId, "voiceID": voiceChannelId})
            return result.channelID
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_voice_channel_id_from_text_channel(self, guildId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.textChannel.find_one({"guildId": guildId, "channelID": textChannelId})
            return result.voiceID
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clean_tracked_channels(self, guildId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            self.connection.voiceChannel.delete_many({"guildID": guildId, "voiceID": voiceChannelId})
            self.connection.textChannel.delete_many({"guildID": guildId, "channelID": textChannelId})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_tracked_voice_channel_id_by_owner(self, guildId, ownerId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ? AND userID = ?", (guildId, ownerId,))
            items = self.connection.voiceChannel.find({"guildID": guildId, "userID": ownerId}, {"voiceID": 1})
            channel_ids = [item.voiceID for item in items]
            return channel_ids
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_channel_owner_id(self, guildId, channelId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT userID FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildId, channelId,))
            # item = c.fetchone()
            # if item:
            #     return int(item[0])
            # c.execute("SELECT userID FROM textChannel WHERE guildID = ? AND channelID = ?", (guildId, channelId,))
            # item = c.fetchone()
            # if item:
            #     return int(item[0])

            # return None
            item = self.connection.voiceChannel.find_one({"guildID": guildId, "voiceID": channelId}, {"userID": 1})
            if item:
                return int(item.userID)
            item = self.connection.textChannel.find_one({"guildID": guildId, "channelID": channelId}, {"userID": 1})
            if item:
                return int(item.userID)
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_user_settings(self, guildId, userId):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (userId, guildId,))
            r = self.connection.userSettings.find_one({"guildID": guildId, "userID": userId})
            if r:
                return settings.UserSettings(guildId=guildId, userId=userId, channelName=r.channelName, channelLimit=int(r.channelLimit), bitrate=int(r.bitrate), defaultRole=r.defaultRole)
            else:
                return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_guild_settings(self, guildId):
        try:
            if self.connection is None:
                self.open()
            rows = self.connection.guild.find({"guildID": guildId})
            if rows:
                result = settings.GuildSettings(guildId=guildId)
                for r in rows:
                    result.channels.append(settings.GuildCategoryChannel(ownerId=(r.ownerID), categoryId=int(r.voiceCategoryID), channelId=int(r.voiceChannelID), useStage=r.useStage))
                return result
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def update_guild_settings(self, guildId, createChannelId, categoryId, ownerId, useStage: bool):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            stageInt = 0
            if useStage:
                stageInt = 1
            self.connect.guild.find_one_and_update({"guildID": guildId, "voiceChannelID": createChannelId}, { "$set": { "ownerID": ownerId, "voiceCategoryID": categoryId, "useStage": stageInt } })
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def insert_guild_settings(self, guildId, createChannelId, categoryId, ownerId, useStage: bool):
        try:
            if self.connection is None:
                self.open()
            stageInt = 0
            if useStage:
                stageInt = 1
            payload = {
                "guildID": guildId,
                "ownerID": ownerId,
                "voiceChannelID": createChannelId,
                "voiceCategoryID": categoryId,
                "useStage": stageInt
            }
            result = self.connection.guild.insert_one(payload)
            # c.execute("INSERT INTO guild VALUES (?, ?, ?, ?, ?)", (guildId, ownerId, createChannelId, categoryId, stageInt))
            return result is not None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def set_guild_category_settings(self, guildId, categoryId, channelLimit, channelLocked, bitrate, defaultRole):
        try:
            if not self.connection:
                self.open()
            # c = self.connection.cursor()
            cat_settings = self.get_guild_category_settings(guildId=guildId, categoryId=categoryId)
            if cat_settings:
                payload = { "channelLimit": channelLimit, "channelLocked": channelLocked, "bitrate": bitrate, "defaultRole": defaultRole }
                self.connection.guildCategorySettings.find_one_and_update({"guildID": guildId, "voiceCategoryID": categoryId}, { "$set": payload })
                # c.execute("UPDATE guildCategorySettings SET channelLimit = ?, channelLocked = ?, bitrate = ?, defaultRole = ? WHERE guildID = ? AND voiceCategoryID = ?", (channelLimit, channelLocked, bitrate, defaultRole, guildId, CategoryChannelConverter,))
            else:
                # c.execute("INSERT INTO guildCategorySettings VALUES ( ?, ?, ?, ?, ?, ? )", (guildId, CategoryChannelConverter, channelLimit, channelLocked, bitrate, defaultRole,))
                payload = {
                    "guildID": guildId,
                    "voiceCategoryID": categoryId,
                    "channelLimit": channelLimit,
                    "channelLocked": channelLocked,
                    "bitrate": bitrate,
                    "defaultRole": defaultRole
                }
                self.connection.guildCategorySettings.insert_one(payload)
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
    def get_guild_category_settings(self, guildId, categoryId):
        try:
            if self.connection is None:
                self.open()
            row = self.connection.guildCategorySettings.find_one({ "guildID": guildId, "voiceCategoryID": categoryId})
            if row:
                result = settings.GuildCategorySettings(guildId=guildId, categoryId=categoryId, channelLimit=row.channelLimit, channelLocked=row.channelLocked, bitrate=row.bitrate, defaultRole=row.defaultRole)
                return result
            # c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildId, categoryId,))
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
            self.connection.userSettings.find_one_and_update({ "guildID": guildId, "userID": userId }, { "$set": { "channelName": channelName }})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def update_user_limit(self, guildId, userId, limit: int = 0):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
            self.connection.userSettings.find_one_and_update({ "guildID": guildId, "userID": userId }, { "$set": { "channelLimit": limit }})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def update_user_bitrate(self, guildId, userId, bitrate: int = 8):
        try:
            if self.connection is None:
                self.open()
            # c = self.connection.cursor()
            # c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
            self.connection.userSettings.find_one_and_update({ "guildID": guildId, "userID": userId }, { "$set": { "bitrate": bitrate }})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def insert_user_settings(self, guildId, userId, channelName, channelLimit, bitrate: int, defaultRole: str):
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
                "defaultRole": defaultRole
            }
            self.connection.userSettings.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_guild_create_channels(self, guildId):
        pass
    def get_use_stage_on_create(self, guildId, channelId, categoryId):
        pass
    def add_tracked_text_channel(self, guildId, ownerId, voiceChannelId, textChannelId):
        pass
    def delete_tracked_text_channel(self, guildId, voiceChannelId, textChannelId):
        pass
    def track_new_voice_channel(self, guildId, ownerId, voiceChannelId):
        pass
    def track_new_channel_set(self, guildId, ownerId, voiceChannelId, textChannelId):
        pass
    def get_tracked_channels_for_guild(self, guildId):
        pass
    def get_tracked_channel_owner(self, guildId, voiceChannelId):
        pass
    def clean_guild_user_settings(self, guildId):
        pass
    def get_default_role(self, guildId, categoryId, userId):
        pass
    def set_default_role_for_user(self, guildId, userId, defaultRole):
        pass
    def set_default_role_for_category(self, guildId, categoryId, defaultRole):
        pass
