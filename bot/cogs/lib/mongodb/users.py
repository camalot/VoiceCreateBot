import datetime
import traceback
import discord

from bot.cogs.lib import utils
from bot.cogs.lib.database import Database
from bot.cogs.lib.member_status import MemberStatus


class UsersMongoDatabase(Database):
    def __init__(self):
        super().__init__()
        pass

    def track_user(self, user: discord.Member):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(user.guild.id),
                "name": user.name,
                "discriminator": user.discriminator,
                "nick": user.nick,
                "display_name": user.display_name,
                "user_id": str(user.id),
                "created_at": utils.to_timestamp(user.created_at),
                "avatar": user.avatar.url if user.avatar else user.default_avatar.url,
                "status": MemberStatus.from_discord(user.status),
                "bot": user.bot,
                "system": user.system,
                "timestamp": timestamp,
            }

            self.connection.users.update_one({ "guild_id": str(user.guild.id), "user_id": str(user.id) }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection is not None:
                self.close()
