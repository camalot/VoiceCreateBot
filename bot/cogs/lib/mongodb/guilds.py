import datetime
import traceback
import discord

from bot.cogs.lib import utils
from bot.cogs.lib.mongodb.database import Database


class GuildsMongoDatabase(Database):

    def __init__(self):
        super().__init__()
        pass

    def track_guild(self, guild: discord.Guild):
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
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection is not None:
                self.close()
