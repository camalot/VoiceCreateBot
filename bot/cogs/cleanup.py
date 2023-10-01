import inspect
import os
import traceback

import discord
from bot.cogs.lib import logger, mongo, utils, settings
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.channels import Channels
from bot.cogs.lib.mongodb.channels import ChannelsDatabase
from bot.cogs.lib.mongodb.guilds import GuildsMongoDatabase
from discord.ext import commands

class CleanupCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.channel_helper = Channels(bot)

        self.channel_db = ChannelsDatabase()
        self.guild_db = GuildsMongoDatabase()

        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._module} cog")

    async def clean_up_tracked_channels(self, guildID):
        _method = inspect.stack()[1][3]
        self.log.debug(guildID, f"{self._module}.{self._class}.{_method}", "Clean up tracked channels")
        try:
            self.log.debug(guildID, f"{self._module}.{self._class}.{_method}", "checking guild create channels")
            createChannelSettings = None
            createChannelSettings = self.guild_db.get_guild_create_channel_settings(guildId=guildID)
            if createChannelSettings and createChannelSettings.channels:
                for cc in createChannelSettings.channels:
                    cc_channel = await self.channel_helper.get_or_fetch_channel(cc.channel_id)
                    if not cc_channel:
                        # delete this channel as it no longer exists.
                        self.log.debug(
                            guildId=guildID,
                            method=f"{self._module}.{self._class}.{_method}",
                            message=f"Deleting create channel {cc.channel_id} as it does not exist",
                        )
                        self.guild_db.delete_guild_create_channel(
                            guildId=guildID, channelId=cc.channel_id, categoryId=cc.category_id
                        )
                        pass
                    else:
                        # check the category and update if necessary
                        cc_category = cc_channel.category
                        if not cc_category:
                            # what if its not in a category at all?
                            self.log.debug(
                                guildID,
                                f"{self._module}.{self._class}.{_method}",
                                "Create Channel is no longer in a category",
                            )
                        else:
                            # check if the category is the same that we have tracked
                            if cc.category_id != cc_category.id:
                                self.log.debug(
                                    guildID, f"{self._module}.{self._class}.{_method}", "Category ID is different"
                                )
                                self.settings.db.update_guild_create_channel_settings(
                                    guildId=guildID,
                                    createChannelId=cc.channel_id,
                                    categoryId=cc_category.id,
                                    ownerId=cc.owner_id,
                                    useStage=cc.use_stage,
                                )
            self.log.debug(guildID, f"{self._module}.{self._class}.{_method}", "checking user created channels")
            trackedChannels = self.channel_db.get_tracked_voice_channel_ids(guildID)
            if trackedChannels is None or len(trackedChannels) == 0:
                self.log.debug(guildID, f"{self._module}.{self._class}.{_method}", "No tracked channels")
                return
            for vc in trackedChannels:
                self.log.debug(guildID, f"{self._module}.{self._class}.{_method}", f"Checking {vc}")
                textChannel = None
                voiceChannelId = vc
                if voiceChannelId:
                    self.log.debug(guildID, f"{self._module}.{self._class}.{_method}", f"Checking {voiceChannelId}")
                    voiceChannel = await self.channel_helper.get_or_fetch_channel(voiceChannelId)

                    textChannelId = self.channel_db.get_text_channel_id(guildID, voiceChannelId) or None
                    if textChannelId:
                        textChannel = await self.channel_helper.get_or_fetch_channel(textChannelId)

                    if not textChannel:
                        self.log.debug(
                            guildID,
                            f"{self._module}.{self._class}.{_method}",
                            f"Unable to find text channel: {textChannelId}",
                        )

                    if voiceChannel:
                        self.log.debug(
                            guildID,
                            f"{self._module}.{self._class}.{_method}",
                            f"Found voice channel: {voiceChannelId}",
                        )
                        # how old is the channel?
                        created_at = utils.to_timestamp(voiceChannel.created_at)
                        # check if the channel is less than 5 seconds old
                        skip_window = 5
                        if created_at + skip_window > utils.get_timestamp():
                            self.log.debug(
                                guildID,
                                f"{self._module}.{self._class}.{_method}",
                                f"Skipping Channel {voiceChannel} because it is too new",
                            )
                            continue

                        if len(voiceChannel.members) == 0 and len(voiceChannel.voice_states) == 0:
                            self.log.debug(
                                guildID,
                                f"{self._module}.{self._class}.{_method}",
                                f"Start Tracked Cleanup: {voiceChannelId}",
                            )
                            self.log.debug(
                                guildID,
                                f"{self._module}.{self._class}.{_method}",
                                f"Deleting Channel {voiceChannel} because everyone left",
                            )
                            self.channel_db.clean_tracked_channels(
                                guildId=guildID, voiceChannelId=voiceChannelId, textChannelId=textChannelId)
                            if textChannel:
                                await textChannel.delete()
                            await voiceChannel.delete()
                        else:
                            self.log.debug(
                                guildID,
                                f"{self._module}.{self._class}.{_method}",
                                f"Skipping Channel {voiceChannel} because it is not empty",
                            )
                    else:
                        self.log.debug(
                            guildID,
                            f"{self._module}.{self._class}.{_method}",
                            f"Unable to find voice channel: {voiceChannelId}",
                        )
                        self.channel_db.clean_tracked_channels(guildID, voiceChannelId, textChannelId)
                else:
                    self.log.debug(guildID, f"{self._module}.{self._class}.{_method}", f"Unable to find voice channel")
        except discord.errors.NotFound as nf:
            self.log.warn(guildID, f"{self._module}.{self._class}.{_method}", str(nf), traceback.format_exc())
            self.log.debug(guildID, f"{self._module}.{self._class}.{_method}", f"Channel Not Found. Already Cleaned Up")
        except Exception as ex:
            self.log.error(guildID, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_ready(self):
        _method = inspect.stack()[0][3]
        for guild in self.bot.guilds:
            await self.clean_up_tracked_channels(guild.id)
            # self.set_guild_strings(guild.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        _method = inspect.stack()[1][3]
        guild_id = member.guild.id
        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"On Voice State Update")
        await self.clean_up_tracked_channels(guild_id)

async def setup(bot):
    await bot.add_cog(CleanupCog(bot))
