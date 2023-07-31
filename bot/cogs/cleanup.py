import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import inspect
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import logger
from .lib import loglevel
from .lib.channels import Channels

class CleanupCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.channel_helper = Channels(bot)

        self.db = mongo.MongoDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", f"Logger initialized with level {log_level.name}")
        self.log.debug(0, f"{self._module}.{_method}", f"Initialized {self._module} cog")

    async def clean_up_tracked_channels(self, guildID):
        _method = inspect.stack()[1][3]
        self.log.debug(guildID, f"{self._module}.{_method}" , "Clean up tracked channels")
        try:
            self.db.open()
            self.log.debug(guildID, f"{self._module}.{_method}" , "checking guild create channels")
            createChannelSettings = self.db.get_guild_create_channel_settings(guildId=guildID)
            if createChannelSettings and createChannelSettings.channels:
                for cc in createChannelSettings.channels:
                    cc_channel = await self.channel_helper.get_or_fetch_channel(cc.channel_id)
                    if not cc_channel:
                        # delete this channel as it no longer exists.
                        self.log.debug(guildID, f"{self._module}.{_method}" , f"Deleting create channel {cc.channel_id} as it does not exist")
                        self.db.delete_guild_create_channel(guildId=guildID, channelId=cc.channel_id, categoryId=cc.category_id)
                        pass
                    else:
                        # check the category and update if necessary
                        cc_category = cc_channel.category
                        if not cc_category:
                            # what if its not in a category at all?
                            self.log.debug(guildID, f"{self._module}.{_method}" , "Create Channel is no longer in a category")
                        else:
                            # check if the category is the same that we have tracked
                            if cc.category_id != cc_category.id:
                                self.log.debug(guildID, f"{self._module}.{_method}" , "Category ID is different")
                                self.db.update_guild_create_channel_settings(guildId=guildID, createChannelId=cc.channel_id, categoryId=cc_category.id, ownerId=cc.owner_id, useStage=cc.use_stage)
            self.log.debug(guildID, f"{self._module}.{_method}" , "checking user created channels")
            trackedChannels = self.db.get_tracked_voice_channel_ids(guildID)
            if trackedChannels is None:
                return
            for vc in trackedChannels:
                textChannel = None
                voiceChannelId = vc
                if voiceChannelId:
                    voiceChannel = await self.channel_helper.get_or_fetch_channel(voiceChannelId)

                    textChannelId = self.db.get_text_channel_id(guildID, voiceChannelId)
                    if textChannelId:
                        textChannel = await self.channel_helper.get_or_fetch_channel(textChannelId)

                    if voiceChannel:
                        # how old is the channel?
                        created_at = utils.to_timestamp(voiceChannel.created_at)
                        # if created at is less than skip window, skip it
                        skip_window = 5
                        if created_at > (utils.get_timestamp() - skip_window):
                            continue

                        if len(voiceChannel.members) == 0 and len(voiceChannel.voice_states) == 0:
                            self.log.debug(guildID, f"{self._module}.{_method}" , f"Start Tracked Cleanup: {voiceChannelId}")
                            self.log.debug(guildID, f"{self._module}.{_method}" , f"Deleting Channel {voiceChannel} because everyone left")
                            self.db.clean_tracked_channels(guildID, voiceChannelId, textChannelId)
                            if textChannel:
                                await textChannel.delete()
                            await voiceChannel.delete()
                    else:
                        self.log.debug(guildID, f"{self._module}.{_method}" , f"Unable to find voice channel: {voiceChannelId}")
                        self.db.clean_tracked_channels(guildID, voiceChannelId, textChannelId)
        except discord.errors.NotFound as nf:
            self.log.warn(guildID, f"{self._module}.{_method}", str(nf), traceback.format_exc())
            self.log.debug(guildID, f"{self._module}.{_method}" , f"Channel Not Found. Already Cleaned Up")
        except Exception as ex:
            self.log.error(guildID, f"{self._module}.{_method}", str(ex), traceback.format_exc())
        finally:
             self.db.close()

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
        self.log.debug(guild_id, f"{self._module}.{_method}" , f"On Voice State Update")
        await self.clean_up_tracked_channels(guild_id)

async def setup(bot):
    await bot.add_cog(CleanupCog(bot))