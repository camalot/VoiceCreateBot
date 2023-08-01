from .. import settings
import discord
from pymongo import MongoClient
import traceback
import json
from .. import utils
from .database import Database
import datetime

class UserSettingsMongoDatabase(Database):

    def __init__(self):
        super().__init__()
        pass

    def get_user_settings(self, guildId: int, userId: int):
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (userId, guildId,))
            r = self.connection.user_settings.find_one({"guild_id": str(guildId), "user_id": str(userId)})
            if r:
                return settings.UserSettings(guildId=guildId, userId=userId, channelName=r['channelName'], channelLimit=int(r['channelLimit']), bitrate=int(r['bitrate']), defaultRole=r['defaultRole'], autoGame=r['auto_game'])
            else:
                return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
