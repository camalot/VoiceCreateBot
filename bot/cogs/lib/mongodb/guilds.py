import datetime
import inspect
import os
import traceback
import discord

from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.database import Database


class GuildsMongoDatabase(Database):

    def __init__(self):
        _method = inspect.stack()[0][3]
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.log(
            guildId=0,
            level=LogLevel.DEBUG,
            method=f"{self._module}.{self._class}.{_method}",
            message=f"Initialized {self._class}",
        )
        pass

    def get_guild_create_channels(self, guildId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildId,))
            cursor = self.connection.create_channels.find({"guild_id": str(guildId)}, { "voice_channel_id": 1 })
            result = []
            for c in cursor:
                result.append(int(c['voice_channel_id']))
            return result
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_guild(self, guild: discord.Guild):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild.id),
                "name": guild.name,
                "owner_id": str(guild.owner_id),
                "created_at": utils.to_timestamp(guild.created_at),
                "vanity_url": guild.vanity_url or None,
                "vanity_url_code": guild.vanity_url_code or None,
                "icon": guild.icon.url if guild.icon else None,
                "timestamp": timestamp
            }

            self.connection.guilds.update_one({ "guild_id": str(guild.id) }, { "$set": payload }, upsert=True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
