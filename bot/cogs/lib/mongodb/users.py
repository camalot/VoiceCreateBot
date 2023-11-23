import datetime
import inspect
import traceback
import discord

from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.enums.member_status import MemberStatus
from bot.cogs.lib.enums.user_channel_state import UserChannelState
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
    def track_user_join_channel(self, guild_id: int, user_id: int, channel_id: int):
        self._track_user_channel_history(guild_id, user_id, channel_id, UserChannelState.JOIN)

    # track user leave channel
    def track_user_leave_channel(self, guild_id: int, user_id: int, channel_id: int):
        self._track_user_channel_history(guild_id, user_id, channel_id, UserChannelState.LEAVE)

    def _track_user_channel_history(self, guild_id: int, user_id: int, channel_id: int, state: UserChannelState):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            # if the user state is LEAVE, then we need to find the most recent JOIN record
            # and update it with the LEAVE timestamp and calculate the duration
            if state == UserChannelState.LEAVE:
                # find the most recent JOIN record
                join_record = self.connection.user_channel_history.find_one(
                    {
                        "guild_id": str(guild_id),
                        "user_id": str(user_id),
                        "channel_id": str(channel_id),
                        "leave": None,
                        "state": UserChannelState.JOIN.value,
                    },
                    sort=[("timestamp", -1)],
                )

                # if there is no JOIN record, then we can't update it
                if join_record is None:
                    self.log(
                        guildId=guild_id,
                        level=LogLevel.ERROR,
                        method=f"{self._module}.{self._class}.{_method}",
                        message=f"Unable to find JOIN record for user {user_id} in channel {channel_id} when attempting to update with LEAVE timestamp",
                    )
                    return

                # calculate the duration
                duration = timestamp - join_record["timestamp"]

                # update the JOIN record with the LEAVE timestamp and duration
                self.connection.user_channel_history.update_one(
                    {"_id": join_record["_id"]},
                    {
                        "$set": {
                            "state": state.value,
                            "leave": timestamp,
                            "timestamp": timestamp,
                            "duration": duration,
                        }
                    },
                )
            # if the user state is JOIN, then we need to insert a new record
            elif state == UserChannelState.JOIN:
                # if the user state is JOIN and there is already an open JOIN record, then we need to update it
                # with the new JOIN timestamp
                # find the most recent JOIN record
                join_record = self.connection.user_channel_history.find_one(
                    {
                        "guild_id": str(guild_id),
                        "user_id": str(user_id),
                        "channel_id": str(channel_id),
                        "leave": None,
                        "state": UserChannelState.JOIN.value,
                    },
                    sort=[("timestamp", -1)],
                )

                if join_record is not None:
                    # update the JOIN record with the new JOIN timestamp
                    self.connection.user_channel_history.update_one(
                        {"_id": join_record["_id"]},
                        {
                            "$set": {
                                "state": state.value,
                                "join": timestamp,
                                "timestamp": timestamp,
                            }
                        },
                    )
                    return

                payload = {
                    "guild_id": str(guild_id),
                    "user_id": str(user_id),
                    "channel_id": str(channel_id),
                    "state": state.value,
                    "join": timestamp,
                    "leave": None,
                    "duration": None,
                    "timestamp": timestamp,
                }

                self.connection.user_channel_history.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
