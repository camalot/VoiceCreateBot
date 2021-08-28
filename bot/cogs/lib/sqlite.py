import sqlite3
import traceback
from . import database
from . import settings
class SqliteDatabase(database.Database):
    def __init__(self):
        self.settings = settings.Settings()
        pass
    def open(self):
        self.connection = sqlite3.connect(self.settings.db_path)
        pass
    def close(self):
        if self.connection:
            self.connection.commit()
            self.connection.close()
        pass
    def get_tracked_voice_channel_ids(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ?", (guildId,))
            items = c.fetchall()
            return items
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_text_channel_id(self, guildId, voiceChannelId):
        # SELECT channelID FROM textChannel WHERE guildID = ? and voiceId = ?
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT channelID FROM textChannel WHERE guildID = ? and voiceId = ?", (guildId, voiceChannelId))
            item = c.fetchone()
            return item[0]
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
