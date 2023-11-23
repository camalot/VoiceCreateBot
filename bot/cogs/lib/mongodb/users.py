import datetime
import inspect
import traceback
import discord

from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.enums.member_status import MemberStatus
from bot.cogs.lib.mongodb.database import Database


class UsersDatabase(Database):
    def __init__(self):
        super().__init__()
        pass

    def track_user(self, user: discord.Member):
        _method = inspect.stack()[0][3]
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
                "status": str(MemberStatus.from_discord(user.status)),
                "bot": user.bot,
                "system": user.system,
                "timestamp": timestamp,
            }

            self.connection.users.update_one({ "guild_id": str(user.guild.id), "user_id": str(user.id) }, { "$set": payload }, upsert=True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    # track user join channel

    # track user leave channel
