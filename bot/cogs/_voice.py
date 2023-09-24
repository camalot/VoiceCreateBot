import discord
import math
import asyncio
import json
import datetime
from discord.ext import commands
import traceback
from urllib.parse import quote
from discord.ext.commands.core import guild_only
import validators
from discord.ext.commands.cooldowns import BucketType

from discord.ext.commands import has_permissions, CheckFailure
from time import gmtime, strftime
import os
import glob
import typing
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import logger
from .lib import loglevel

import inspect
class EmbedField():
    def __init__(self, name, value):
        self.name = name
        self.value = value

class voice(commands.Cog):
    def __init__(self, bot):
        self.settings = settings.Settings()
        self.bot = bot

        self.db = mongo.MongoDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "voice.__init__", f"Logger initialized with level {log_level.name}")


        self.strings = {}

    @commands.group()
    async def voice(self, ctx):
        pass

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     for guild in self.bot.guilds:
    #         await self.clean_up_tracked_channels(guild.id)
    #         self.set_guild_strings(guild.id)


    # @commands.Cog.listener()
    # async def on_member_update(self, before, after):
    #     try:
    #         _method = inspect.stack()[1][3]
    #         guild_id = after.guild.id
    #         if not after:
    #             return
    #         is_in_channel = after is not None and after.voice is not None and after.voice.channel is not None
    #         if is_in_channel:
    #             self.db.open()
    #             self.log.debug(guild_id, _method , f"Member Update Start of user: '{after.name}'")
    #             voice_channel = after.voice.channel
    #             voice_channel_id = voice_channel.id
    #             owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
    #             if owner_id != after.id:
    #                 # user is in a channel, but not their channel
    #                 self.log.debug(guild_id, _method , f"User:{str(after.id)} is in a channel, but not their own channel.")
    #                 return
    #             if before.activity == after.activity:
    #                 # we are only looking at activity
    #                 self.log.debug(guild_id, _method , f"Before / After activity is the same")
    #                 return

    #             owner = await self.get_or_fetch_member(after.guild, owner_id)
    #             user_settings = self.db.get_user_settings(guild_id, after.id)

    #             if user_settings and user_settings.auto_game:
    #                 text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
    #                 if text_channel_id:
    #                     text_channel = await self.get_or_fetch_channel(int(text_channel_id))
    #                 self.log.debug(guild_id, _method , f"trigger auto game change")
    #                 selected_title = voice_channel.name
    #                 if owner and text_channel:
    #                     selected_title = await self.ask_game_for_user(targetChannel=text_channel, user=owner, title=self.get_string(guild_id, 'title_update_to_game'))
    #                     if selected_title:
    #                         if voice_channel.name != selected_title:
    #                             if text_channel:
    #                                 self.log.debug(guild_id, _method , f"Change Text Channel Name: {selected_title}")
    #                                 await text_channel.edit(name=selected_title)
    #                                 await self.sendEmbed(text_channel, self.get_string(guild_id, 'title_update_channel_name'), f'{after.mention}, {utils.str_replace(self.get_string(guild_id, "info_channel_name_change"), name=selected_title)}', delete_after=5)
    #                             await voice_channel.edit(name=selected_title)
    #                     else:
    #                         self.log.debug(guild_id, _method , f"Unable to retrieve a valid title from game.")
    #                 else:
    #                     self.log.debug(guild_id, _method , f"owner is none, or text_channel is none. Can't ask to choose game.")
    #                     game_activity = [a for a in after.activities if a.type == discord.ActivityType.playing]
    #                     stream_activity = [a for a in after.activities if a.type == discord.ActivityType.streaming]
    #                     watch_activity = [a for a in after.activities if a.type == discord.ActivityType.watching]
    #                     if game_activity:
    #                         selected_title = game_activity[0].name
    #                     elif stream_activity:
    #                         selected_title = stream_activity[0].game
    #                     elif watch_activity:
    #                         selected_title = watch_activity[0].name

    #                     if selected_title:
    #                         if voice_channel.name != selected_title:
    #                             if text_channel:
    #                                 self.log.debug(guild_id, _method , f"Change Text Channel Name: {selected_title}")
    #                                 await text_channel.edit(name=selected_title)
    #                             self.log.debug(guild_id, _method , f"Change Voice Channel Name: {selected_title}")
    #                             await voice_channel.edit(name=selected_title)
    #             else:
    #                 self.log.debug(guild_id, _method , f"trigger name change, but setting is false.")
    #     except discord.errors.NotFound as nf:
    #         self.log.warn(guild_id, _method, str(nf), traceback.format_exc())
    #     except Exception as ex:
    #         self.log.error(guild_id, _method , str(ex), traceback.format_exc())
    #     finally:
    #         self.db.close()

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        try:
            _method = inspect.stack()[1][3]
            self.db.open()
            if before and after:
                if before.id == after.id:
                    # This handles a manual channel rename. it changes the text channel name to match.
                    guild_id = before.guild.id or after.guild.id
                    channel = await self.get_or_fetch_channel(after.id)
                    if not channel.category:
                        self.log.debug(guild_id, _method, "Unable to locate category", traceback.format_exc())
                        return
                    category_id = channel.category.id
                    owner_id = self.db.get_channel_owner_id(guild_id, after.id)
                    if owner_id:
                        owner = await self.get_or_fetch_member(before.guild, owner_id)
                        if not owner:
                            self.log.warn(guild_id, _method, f"Unable to find owner [user:{owner_id}] for the channel: {channel}")
                            return

                        if before.name == after.name:
                            # same name. ignore
                            self.log.debug(guild_id, _method , "Channel Names are the same. Nothing to do")
                            return
                        else:
                            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
                            self.log.debug(guild_id, _method, f"default_role: {default_role}")
                            temp_default_role = self.get_by_name_or_id(after.guild.roles, default_role)
                            self.log.debug(guild_id, _method, f"temp_default_role: {temp_default_role}")
                            user_settings = self.db.get_user_settings(guild_id, owner_id)

                            self.log.debug(guild_id, _method , f"Channel Type: {after.type}")

                            if after.type == discord.ChannelType.voice:
                                # new channel name
                                text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=after.id)
                                if text_channel_id:
                                    text_channel = await self.get_or_fetch_channel(int(text_channel_id))
                                if text_channel:
                                    self.log.debug(guild_id, _method , f"Change Text Channel Name: {after.name}")
                                    await text_channel.edit(name=after.name)
                                    await self.sendEmbed(text_channel, self.get_string(guild_id, 'title_update_channel_name'), f'{owner.mention}, {utils.str_replace(self.get_string(guild_id, "info_channel_name_change"), channel=text_channel.name)}', delete_after=5)
                            if after.type == discord.ChannelType.text:
                                voiceChannel = None
                                voice_channel_id = self.db.get_voice_channel_id_from_text_channel(guildId=guild_id, textChannelId=after.id)
                                if voice_channel_id:
                                    voiceChannel = await self.get_or_fetch_channel(voice_channel_id)
                                if voiceChannel:
                                    self.log.debug(guild_id, _method , f"Change Voice Channel Name: {after.name}")
                                    await voiceChannel.edit(name=after.name)
                                    await self.sendEmbed(after, self.get_string(guild_id, 'title_update_channel_name'), f'{owner.mention}, {utils.str_replace(self.get_string(guild_id, "info_channel_name_change"), channel=after.name)}', delete_after=5)


                            if user_settings:
                                self.db.update_user_channel_name(guildId=guild_id, userId=owner_id, channelName=after.name)
                            else:
                                self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=after.name, channelLimit=0, bitrate=self.settings.BITRATE_DEFAULT, defaultRole=temp_default_role.id, autoGame=False)
        except discord.errors.NotFound as nf:
            self.log.warn(guild_id, _method, str(nf), traceback.format_exc())
        except Exception as e:
            self.log.error(guild_id, _method , str(e), traceback.format_exc())
        finally:
            self.db.close()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        self.db.open()
        _method = inspect.stack()[1][3]
        guild_id = member.guild.id
        self.log.debug(guild_id, _method , f"On Voice State Update")
        # await self.clean_up_tracked_channels(guild_id)
        # await asyncio.sleep(2)
        voiceChannels = self.db.get_guild_create_channels(guild_id)
        if voiceChannels is None:
            self.log.debug(guild_id, _method , f"No voice create channels found for GuildID: {guild_id}")
            pass
        else:
            try:
                self.log.debug(guild_id, _method , f"Check for user in Create Channel")
                if after.channel is not None and after.channel.id in voiceChannels:
                    # User Joined the CREATE CHANNEL
                    self.log.debug(guild_id, _method , f"User requested to CREATE CHANNEL")
                    category_id = after.channel.category_id
                    source_channel = after.channel
                    source_channel_id = after.channel.id
                    channel_owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=source_channel_id)
                    userSettings = self.db.get_user_settings(guildId=guild_id, userId=channel_owner_id or member.id)
                    guildSettings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
                    useStage = self.db.get_use_stage_on_create(guildId=guild_id, channelId=source_channel_id, categoryId=category_id) or 0
                    # CHANNEL SETTINGS START
                    limit = 0
                    locked = False
                    bitrate = self.settings.BITRATE_DEFAULT
                    name = utils.get_random_name()

                    default_role_id = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=member.id)
                    default_role = self.get_by_name_or_id(member.guild.roles, default_role_id) or member.guild.default_role
                    if userSettings is None:
                        if guildSettings is not None:
                            limit = guildSettings.channel_limit
                            locked = guildSettings.channel_locked
                            bitrate = guildSettings.bitrate
                    else:
                        name = userSettings.channel_name
                        if guildSettings is None:
                            limit = userSettings.channel_limit
                            bitrate = userSettings.bitrate
                            locked = False
                        elif guildSettings is not None:
                            limit = userSettings.channel_limit or guildSettings.channel_limit
                            locked = guildSettings.channel_locked or False
                            bitrate = userSettings.bitrate or guildSettings.bitrate
                        else:
                            limit = userSettings.channel_limit
                            locked = guildSettings.channel_locked
                            bitrate = guildSettings.bitrate
                    # CHANNEL SETTINGS END

                    mid = member.id
                    category = discord.utils.get(member.guild.categories, id=category_id)
                    self.log.debug(guild_id, _method , f"Creating channel {name} in {category} with bitrate {bitrate}kbps")
                    is_community = member.guild.features.count("COMMUNITY") > 0
                    if(useStage and is_community):
                        self.log.debug(guild_id, _method , f"Creating Stage Channel")
                        stage_topic = utils.get_random_name(noun_count=1, adjective_count=2)
                        voiceChannel = await member.guild.create_stage_channel(name, topic=stage_topic, category=category, reason="Create Channel Request by {member}", position=0)
                    else:
                        self.log.debug(guild_id, _method , f"Created Voice Channel")
                        voiceChannel = await source_channel.clone(name=name, reason="Create Channel Request by {member}")
                        # voiceChannel = await member.guild.create_voice_channel(name, category=category, reason="Create Channel Request by {member}")
                        # await voiceChannel.edit(sync_permissions=True)
                    textChannel = await member.guild.create_text_channel(name, category=category, position=0)
                    await textChannel.edit(sync_permissions=True)
                    channelID = voiceChannel.id

                    self.log.debug(guild_id, _method , f"Moving {member} to {voiceChannel}")
                    await member.move_to(voiceChannel)
                    # if the bot cant do this, dont fail...
                    try:
                        self.log.debug(guild_id, _method , f"Setting permissions on {voiceChannel}")
                        # if use_voice_activity is not True, some cases where people cant speak, unless they use P2T
                        await voiceChannel.set_permissions(member, speak=True, priority_speaker=True, connect=True, read_messages=True, send_messages=True, view_channel=True, use_voice_activation=True, stream=True, move_members=True)
                        await textChannel.set_permissions(member, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    except Exception as ex:
                        self.log.error(guild_id, _method , str(ex), traceback.format_exc())
                    self.log.debug(guild_id, _method , f"Set user limit to {limit} on {voiceChannel}")
                    await voiceChannel.edit(name=name, user_limit=limit, bitrate=(bitrate*1000), position=0)

                    self.log.debug(guild_id, _method , f"Track voiceChannel userID: {mid} channelID: {channelID}")
                    self.log.debug(guild_id, _method , f"Track Voice and Text Channels {name} in {category}")

                    self.db.track_new_channel_set(guildId=guild_id, ownerId=mid, voiceChannelId=channelID, textChannelId=textChannel.id)

                    try:
                        if default_role:
                            self.log.debug(guild_id, _method , f"Check if bot can set channel for {default_role.name} {voiceChannel}")
                            await textChannel.set_permissions(default_role, read_messages=(not locked), send_messages=(not locked), read_message_history=(not locked), view_channel=True)
                            await voiceChannel.set_permissions(default_role, speak=True, connect=(not locked), read_messages=(not locked), send_messages=(not locked), view_channel=True, stream=(not locked), use_voice_activation=True, move_members=True)
                    except Exception as ex:
                        self.log.error(guild_id, _method , str(ex), traceback.format_exc())

                    await self.sendEmbed(textChannel, self.get_string(guild_id, 'title_new_voice_text_channel'), f"{member.mention}, {self.get_string(guild_id, 'info_new_voice_text_channel')}", delete_after=None, footer=None)
                    # initMessage contains keys that point to strings in the language file.
                    initMessage = self.settings.initMessage
                    if initMessage:
                        # title, message, fields=None, delete_after=None, footer=None
                        fields = []
                        for f in range(len(initMessage['fields'])):
                            fields.append(EmbedField(self.get_string(guild_id, initMessage['fields'][f]['name']), initMessage['fields'][f]['value']).__dict__)
                        await self.sendEmbed(textChannel, self.get_string(guild_id, initMessage['title']), f"{member.mention}, {self.get_string(guild_id, initMessage['message'])}", fields=fields, delete_after=None, footer=None)
            except discord.errors.NotFound as nf:
                self.log.warn(guild_id, _method , str(nf))
            except Exception as ex:
                self.log.error(guild_id, _method , str(ex), traceback.format_exc())

    @voice.command()
    async def version(self, ctx):
        author = ctx.author
        appName = utils.dict_get(self.settings.__dict__, "name", default_value = "Voice Create Bot")
        await self.sendEmbed(ctx.channel, self.get_string(ctx.guild.id, 'title_version'), f"{author.mention}, {appName} version: {self.settings.APP_VERSION}", delete_after=10)
        await ctx.message.delete()

    @voice.command()
    @has_permissions(administrator=True)
    async def channels(self, ctx):
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_id = ctx.author.guild.id
        author = ctx.author
        try:
            if self.isAdmin(ctx):
                guild_channels = self.db.get_tracked_channels_for_guild(guildId=guild_id)
                channelFields = list()
                for vc in guild_channels.voice_channels:
                    voice_channel = await self.get_or_fetch_channel(vc.voice_channel_id)
                    user = await self.get_or_fetch_user(vc.owner_id)
                    text_channel = None
                    tchanName = self.get_string(guild_id, "info_no_text_channel")
                    chanName = self.get_string(guild_id, "info_no_voice_channel")
                    userName = self.get_string(guild_id, "info_no_user")

                    text_channel_filter = [tc for tc in guild_channels.text_channels if tc.voice_channel_id == vc.voice_channel_id]
                    if text_channel_filter:
                        text_channel = await self.get_or_fetch_channel(text_channel_filter[0].text_channel_id)
                        if text_channel:
                            tchanName = f"#{text_channel.name}"
                    if user:
                        userName = f"{user.name}#{user.discriminator}"
                    if text_channel:
                        tchanName = f"#{text_channel.name}"
                    if voice_channel:
                        chanName = voice_channel.name
                    channelFields.append({
                        "name": f"{chanName} / {tchanName}",
                        "value": userName
                    })
                if len(channelFields) > 0:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_tracked_channels'), f"{author.mention}, {self.get_string(guild_id, 'info_tracked_channels')}", fields=channelFields, delete_after=30)
                else:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_tracked_channels'), f"{author.mention}, {self.get_string(guild_id, 'info_no_tracked_channels')}", delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["track-text-channel", "ttc"])
    @has_permissions(administrator=True)
    async def track_text_channel(self, ctx, channel: discord.TextChannel = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.author.guild.id
        self.db.open()
        try:
            if self.isAdmin(ctx):

                voiceChannel = None
                if ctx.author.voice:
                    voiceChannel = ctx.author.voice.channel

                if channel is None:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_no_channel_to_track')}", fields=None, delete_after=5)
                    await ctx.message.delete()
                    return

                if voiceChannel:
                    # check if this voice channel is tracked.
                    tracked = self.db.get_tracked_channels_for_guild(guildId=guild_id)
                    tracked_voice_filter = [tv for tv in tracked.voice_channels if tv.voice_channel_id == voiceChannel.id]
                    tracked_text_filter = [tt for tt in tracked.text_channels if tt.voice_channel_id == voiceChannel.id]
                    if tracked_voice_filter:
                        tracked_voice = tracked_voice_filter[0]
                        if not tracked_text_filter:
                            # no tracked text channel
                            if channel.category_id == voiceChannel.category_id:
                                # text channel is in the same category as the voice channel
                                self.db.add_tracked_text_channel(guildId=guild_id, ownerId=tracked_voice.owner_id, voiceChannelId=voiceChannel.id, textChannelId=channel.id)
                                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_now_tracking_text'), channel=channel.name, voice_channel=voiceChannel.name)}", delete_after=5)
                            else:
                                # not in the same category
                                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_tracking_not_supported'), channel=channel.name, voice_channel=voiceChannel.name)}", delete_after=5)
                        else:
                            tracked_text = tracked_text_filter[0]
                            # channel already has a textChannel associated with it.
                            # check if it exists
                            tc_lookup = await self.get_or_fetch_channel(tracked_text.text_channel_id)

                            if tc_lookup:
                                # channel exists. so we just exit
                                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_already_has_channel'), voice_channel=voiceChannel.name)}", delete_after=5)
                            else:
                                # old tracked channel missing
                                self.db.delete_tracked_text_channel(guildId=guild_id, voiceChannelId=voiceChannel.id, textChannelId=tracked_text.text_channel_id)
                                if channel.category_id == voiceChannel.category_id:
                                    # text channel is in the same category as the voice channel
                                    self.db.add_tracked_text_channel(guildId=guild_id, ownerId=tracked_voice.owner_id, voiceChannelId=voiceChannel.id, textChannelId=channel.id)
                                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_now_tracking'), channel=channel.name, voice_channel=voiceChannel.name)}", delete_after=5)
                                else:
                                    # not in the same category
                                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_tracking_not_supported'), channel=channel.name, voice_channel=voiceChannel.name)}", delete_after=5)

                    else:
                        # not tracked
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_voice_not_tracked')}", delete_after=5)
                else:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_not_in_channel')} ", delete_after=5)
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_text_channel'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def track(self, ctx):
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_id = ctx.author.guild.id
        try:
            message_author_id = ctx.author.id
            channel = ctx.author.voice.channel
            if not channel:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_voice_channel'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_not_in_channel')}", delete_after=5)
            else:
                if self.isAdmin(ctx):
                    tracked_channels = self.db.get_tracked_channels_for_guild(guildId=guild_id)
                    filtered = [t for t in tracked_channels.voice_channels if t.voice_channel_id == channel.id]
                    if filtered:
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_voice_channel'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_channel_already_tracked')}", delete_after=5)
                    else:
                        self.db.track_new_voice_channel(guildId=guild_id, ownerId=message_author_id, voiceChannelId=channel.id)
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_track_voice_channel'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_new_voice_channel_tracked'), voice_channel=channel.name)}", delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def owner(self, ctx, member: discord.Member):
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_id = ctx.author.guild.id
        channel = None
        try:
            if self.isInVoiceChannel(ctx):
                channel = ctx.author.voice.channel
            if channel is None:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_set_channel_owner"), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_not_in_channel')}", delete_after=5)
            else:
                owner_id = self.db.get_tracked_channel_owner(guildId=guild_id, voiceChannelId=channel.id)
                if not owner_id:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_set_channel_owner"), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_unmanaged_channel')}", delete_after=5)
                else:
                    if self.isAdmin(ctx) or ctx.author.id == owner_id:
                        self.db.update_tracked_channel_owner(guildId=guild_id, voiceChannelId=channel.id, ownerId=owner_id, newOwnerId=member.id)
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_set_channel_owner"), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_new_owner'), user=member.mention)}", delete_after=5)
                    else:
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_set_channel_owner"), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def resync(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            self.db.open
            category_id = ctx.author.voice.channel.category.id
            voice_channel = None
            voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                voice_channel_id = ctx.author.voice.channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_not_in_channel'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return

            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if not self.isAdmin(ctx) and ctx.author.id != owner_id:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_permission_denied"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_permission_denied")}', delete_after=5)
                return

            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)
            if text_channel:
                await text_channel.edit(sync_permissions=True)
                await text_channel.set_permissions(ctx.author, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)

            await voice_channel.edit(sync_permissions=True)
            # BUG that requires use_voice_activation=True or some users cannot speak.
            await voice_channel.set_permissions(ctx.author, speak=True, priority_speaker=True, connect=True, read_messages=True, send_messages=True, view_channel=True, stream=True, use_voice_activation=True, move_members=True)
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_channel_sync'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_channel_sync")}', delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def private(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            self.db.open()
            author_id = ctx.author.id
            category_id = ctx.author.voice.channel.category.id
            voice_channel = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_not_in_channel'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)

            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_permission_denied")}', delete_after=5)
                return
            owner_user = await self.get_or_fetch_user(owner_id)

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            await ctx.message.delete()
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_channel_private'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_channel_private_progress")}', delete_after=5)
            permRoles = []
            for m in voice_channel.members:
                if m.id != owner_id:
                    permRoles.append(m)
            if everyone:
                denyRoles = [everyone]
            else:
                denyRoles = []
            for gr in ctx.guild.roles:
                denyRoles.append(gr)
            if text_channel:
                await text_channel.edit(sync_permissions=True)
                await text_channel.set_permissions(owner_user, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                for r in permRoles:
                    await text_channel.set_permissions(r, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                # deny everyone else
                for r in denyRoles:
                    await text_channel.set_permissions(r, connect=False, read_messages=False, view_channel=True, read_message_history=False, send_messages=False)
            await voice_channel.edit(sync_permissions=True)
            await voice_channel.set_permissions(owner_user, speak=True, view_channel=True, connect=True, use_voice_activation=True, stream=False )
            for r in permRoles:
                await voice_channel.set_permissions(r, speak=True, view_channel=True, connect=True, use_voice_activation=True, stream=False)
            # deny everyone else
            for r in denyRoles:
                await voice_channel.set_permissions(r, speak=False, view_channel=True, connect=False)
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_channel_private'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_channel_private")}', delete_after=5)

        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()

    @voice.command()
    async def hide(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            self.db.open()
            author_id = ctx.author.id
            category_id = None
            category = None
            voice_channel = None
            voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                category = voice_channel.category
                category_id = category.id
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_not_in_channel'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return

            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            owner = await self.get_or_fetch_user(owner_id)
            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f'{ctx.author.mention}, {self.get_string(guild_id, "title_permission_denied")}', delete_after=5)
                return

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            # everyone = discord.utils.get(ctx.guild.roles, name=default_role)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            permRoles = []
            if everyone:
                permRoles = [everyone]
            if userOrRole:
                permRoles.append(userOrRole)
            if text_channel:
                await text_channel.set_permissions(owner, view_channel=True)
                for r in permRoles:
                    await text_channel.set_permissions(r, view_channel=False)

            await voice_channel.set_permissions(owner, view_channel=True)
            for r in permRoles:
                await voice_channel.set_permissions(r, view_channel=False)

            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_hide"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_channel_hide")}', delete_after=5)

        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
    @voice.command()
    async def show(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        guild_id = ctx.guild.id
        _method = inspect.stack()[1][3]
        try:
            self.db.open()
            author_id = ctx.author.id
            category_id = None
            category = None
            voice_channel = None
            voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                category = voice_channel.category
                category_id = category.id
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_not_in_channel'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return

            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            owner = await self.get_or_fetch_user(owner_id)
            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f'{ctx.author.mention}, {self.get_string(guild_id, "title_permission_denied")}', delete_after=5)
                return

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            permRoles = []
            if everyone:
                permRoles = [everyone]
            if userOrRole:
                permRoles.append(userOrRole)
            if text_channel:
                await text_channel.set_permissions(owner, view_channel=True)
                for r in permRoles:
                    await text_channel.set_permissions(r, view_channel=True)

            await voice_channel.set_permissions(owner, view_channel=True)
            for r in permRoles:
                await voice_channel.set_permissions(r, view_channel=True)

            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_show"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_channel_show")}', delete_after=5)

        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)

    @voice.command()
    async def mute(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        guild_id = ctx.guild.id
        _method = inspect.stack()[1][3]
        try:
            self.db.open()
            author_id = ctx.author.id
            category_id = None
            category = None
            voice_channel = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                category = voice_channel.category
                category_id = category.id
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_not_in_channel'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            owner = await self.get_or_fetch_user(owner_id)

            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f'{ctx.author.mention}, {self.get_string(guild_id, "title_permission_denied")}', delete_after=5)
                return

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            permRoles = []
            if everyone:
                permRoles = [everyone]
            if userOrRole:
                permRoles.append(userOrRole)
            if text_channel:
                await text_channel.set_permissions(owner, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                for r in permRoles:
                    await text_channel.set_permissions(r, send_messages=False)

            await voice_channel.set_permissions(owner, speak=True)
            for r in permRoles:
                await voice_channel.set_permissions(r, speak=False)

            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_mute"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_channel_mute")}', delete_after=5)

        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def unmute(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            self.db.open()
            author_id = ctx.author.id
            category_id = ctx.author.voice.channel.category.id
            voice_channel = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_not_in_channel'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            owner = await self.get_or_fetch_user(owner_id)
            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f'{ctx.author.mention}, {self.get_string(guild_id, "title_permission_denied")}', delete_after=5)
                return

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            permRoles = []
            if everyone:
                permRoles = [everyone]
            if userOrRole:
                permRoles.append(userOrRole)
            if text_channel:
                await text_channel.set_permissions(owner, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                for r in permRoles:
                    await text_channel.set_permissions(r, send_messages=True)

            await voice_channel.set_permissions(owner, speak=True)
            for r in permRoles:
                await voice_channel.set_permissions(r, speak=True)

            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_unmute"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_channel_unmute")}', delete_after=5)

        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    # @voice.command(aliases=["set-prefix"])
    # @has_permissions(administrator=True)
    # async def set_prefix(self, ctx, prefix="."):
    #     _method = inspect.stack()[1][3]
    #     guild_id = ctx.guild.id
    #     if self.isAdmin(ctx):
    #         if prefix:
    #             self.db.set_guild_settings_prefix(ctx.guild.id, prefix)
    #             # self.bot.command_prefix = self.get_prefix
    #             await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_prefix"), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_set_prefix"), prefix=prefix)}', delete_after=10)
    #             await ctx.message.delete()

    @voice.command()
    async def prefix(self, ctx):
        try:
            _method = inspect.stack()[1][3]
            guild_id = ctx.guild.id
            guild_settings = self.db.get_guild_settings(guild_id)
            prefix = "."
            if guild_settings:
                prefix = guild_settings.prefix
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_prefix"), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_get_prefix"), prefix=prefix)}', delete_after=10)
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            await ctx.message.delete()

    @voice.command()
    async def language(self, ctx):
        try:
            if self.isAdmin(ctx):
                _method = inspect.stack()[1][3]
                guild_id = ctx.guild.id
                guild_settings = self.db.get_guild_settings(guild_id)
                language = self.settings.language
                if guild_settings:
                    language = guild_settings.language
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_language"), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_get_language"), language=self.settings.languages[language])}', delete_after=10)
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            await ctx.message.delete()

    @voice.command(aliases=["set-language"])
    async def set_language(self, ctx):
        if self.isAdmin(ctx):
            try:
                _method = inspect.stack()[1][3]
                guild_id = ctx.guild.id
                language = await self.ask_language(ctx, title=self.get_string(guild_id, "title_language"))
                if language:
                    self.db.set_guild_settings_language(guild_id, language)
                    self.set_guild_strings(guild_id)
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_language"), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_set_language"), language=self.settings.languages[language])}', delete_after=10)
                else:
                    self.log.debug(guild_id, _method, "Language was None after ask user to set it.")
            except Exception as ex:
                self.log.error(guild_id, _method , str(ex), traceback.format_exc())
                await self.notify_of_error(ctx)
            finally:
                await ctx.message.delete()

    # @voice.command()
    # async def help(self, ctx, command=""):
    #     _method = inspect.stack()[1][3]
    #     guild_id = ctx.guild.id
    #     try:
    #         command_list = self.settings.commands
    #         if command and command.lower() in command_list:
    #             cmd = command_list[command.lower()]
    #             if not cmd['admin'] or (cmd['admin'] and self.isAdmin(ctx)):
    #                 fields = list()
    #                 fields.append({"name": self.get_string(guild_id, 'help_info_usage'), "value": f"`{cmd['usage']}`"})
    #                 fields.append({"name": self.get_string(guild_id, 'help_info_example'), "value": f"`{cmd['example']}`"})
    #                 fields.append({"name": self.get_string(guild_id, 'help_info_aliases'), "value": f"`{cmd['aliases']}`"})

    #                 await self.sendEmbed(ctx.channel, utils.str_replace(self.get_string(guild_id, ''), command=command.lower()), self.get_string(guild_id, cmd['help']), fields=fields)
    #         else:
    #             filtered_list = list()
    #             if self.isAdmin(ctx):
    #                 filtered_list = [i for i in command_list.keys()]
    #             else:
    #                 filtered_list = [i for i in command_list.keys() if command_list[i]['admin'] == False]

    #             chunked = utils.chunk_list(list(filtered_list), 10)
    #             pages = math.ceil(len(filtered_list) / 10)
    #             page = 1
    #             for chunk in chunked:
    #                 fields = list()
    #                 for k in chunk:
    #                     cmd = command_list[k.lower()]
    #                     if cmd['admin'] and self.isAdmin(ctx):
    #                         fields.append({"name": self.get_string(guild_id, cmd['help']), "value": f"`{cmd['usage']}`"})
    #                         fields.append({"name": self.get_string(guild_id, 'help_info_more_help'), "value": f"`.voice help {k.lower()}`"})
    #                         fields.append({"name": self.get_string(guild_id, 'help_info_admin_title'), "value": self.get_string(guild_id, "help_info_admin")})
    #                     else:
    #                         fields.append({"name": self.get_string(guild_id, cmd['help']), "value": f"`{cmd['usage']}`"})
    #                         fields.append({"name": self.get_string(guild_id, 'help_info_more_help'), "value": f"`.voice help {k.lower()}`"})

    #                 await self.sendEmbed(ctx.channel, f"{self.get_string(guild_id, 'help_info_list_title')} ({page}/{pages})", self.get_string(guild_id, 'help_info_list_description'), fields=fields)
    #                 page += 1
    #     except Exception as ex:
    #         self.log.error(guild_id, _method , str(ex), traceback.format_exc())
    #         await self.notify_of_error(ctx)
    #     await ctx.message.delete()

    @voice.command(pass_context=True)
    @has_permissions(administrator=True)
    async def init(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        if self.isAdmin(ctx):
            self.db.open()
            try:
                author = ctx.author
                author_id = ctx.author.id
                def check_user(m):
                    return m.author.id == author_id
                def check_role(m):
                    if(check_user(m)):
                        # role = discord.utils.get(m.guild.roles,name=m.content)

                        role = self.get_by_name_or_id(m.guild.roles, m.content)
                        if role:
                            return True
                        return False

                selected_guild_role = await self.ask_default_role(ctx, self.get_string(guild_id, 'title_guild_init'))
                if not selected_guild_role:
                    return

                selected_admin_role = await self.ask_admin_role(ctx, self.get_string(guild_id, 'title_guild_init'))
                if not selected_admin_role:
                    return

                language = await self.ask_language(ctx, self.get_string(guild_id, 'title_guild_init'))
                if not language:
                    language = self.settings.language

                # ask bot prefix?
                prefix = "."
                ask_prefix = await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_guild_init'), self.get_string(guild_id, 'ask_prefix'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
                try:
                    prefixResp = await self.bot.wait_for('message', check=check_user, timeout=60.0)
                    await ask_prefix.delete()
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_guild_init'), self.get_string(guild_id, 'took_too_long'), delete_after=5)
                else:
                    prefix = prefixResp.content
                    await prefixResp.delete()


                self.db.insert_or_update_guild_settings(guildId=guild_id, prefix=prefix, defaultRole=selected_guild_role.id, adminRole=selected_admin_role.id, language=language)

                # after update, update the guild strings
                self.set_guild_strings(guild_id)

                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_guild_init'), f"{author.mention}, {self.get_string(guild_id, 'info_init_success')}", delete_after=5)
            except Exception as ex:
                self.log.error(guild_id, _method , str(ex), traceback.format_exc())
                await self.notify_of_error(ctx)
            finally:
                self.db.close()
                await ctx.message.delete()
        else:
            pass

    @voice.command(pass_context=True)
    @has_permissions(administrator=True)
    async def setup(self, ctx):
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_id = ctx.guild.id
        try:
            self.log.debug(guild_id, _method , f"User id triggering setup: {ctx.author.id}")
            author_id = ctx.author.id
            author = ctx.author
            # If the person is the OWNER or an ADMIN
            if self.isAdmin(ctx):
                def check(m):
                    return m.author.id == author_id
                def check_limit(m):
                    if check(m):
                        if m.content.isnumeric():
                            val = int(m.content)
                            return val >= 0 and val <= 100
                        else:
                            return False
                guild_settings = self.db.get_guild_settings(guildId=guild_id)
                if not guild_settings:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_setup'), f"{author.mention}, {self.get_string(guild_id, 'setup_not_configured')}", delete_after=10)
                    return
                # Ask them for the category name
                category = await self.ask_category(ctx)
                if category is None:
                    return
                useStage = False
                is_community = ctx.guild.features.count("COMMUNITY") > 0
                if is_community:
                    useStage = await self.ask_yes_no(ctx, question=self.get_string(guild_id, 'ask_use_stage'), title=self.get_string(guild_id, 'title_voice_channel_setup'))

                name_ask = await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_setup'), self.get_string(guild_id, 'ask_create_channel_name'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
                try:
                    channelName = await self.bot.wait_for('message', check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_setup'), self.get_string(guild_id, 'took_too_long'), delete_after=5)
                else:
                    try:
                        channel = await ctx.guild.create_voice_channel(channelName.content, category=category)
                        await channelName.delete()
                        await name_ask.delete()

                        guild_cc_settings = self.db.get_guild_create_channel_settings(guildId=guild_id)

                        if guild_cc_settings:
                            if len([c for c in guild_cc_settings.channels if c.category_id == category.id and c.channel_id == channel.id]) >= 1:
                                self.db.update_guild_create_channel_settings(guildId=guild_id, createChannelId=channel.id, categoryId=category.id, ownerId=author_id, useStage=useStage)
                            else:
                                self.db.insert_guild_create_channel_settings(guildId=guild_id, createChannelId=channel.id, categoryId=category.id, ownerId=author_id, useStage=useStage)
                        else:
                            self.db.insert_guild_create_channel_settings(guildId=guild_id, createChannelId=channel.id, categoryId=category.id, ownerId=author_id, useStage=useStage)

                        guild_category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category.id)
                        if not guild_category_settings:

                            defaultLimit = await self.ask_limit(ctx, self.get_string(guild_id, 'title_voice_channel_setup'))

                            locked = await self.ask_yes_no(ctx, question=self.get_string(guild_id, 'ask_default_locked'), title=self.get_string(guild_id, 'title_voice_channel_setup'))

                            defaultBitrate = await self.ask_bitrate(ctx, title=self.get_string(guild_id, 'title_voice_channel_setup'))

                            selected_guild_role = await self.ask_default_role(ctx, self.get_string(guild_id, 'title_voice_channel_setup'))
                            if not selected_guild_role:
                                selected_guild_role = self.get_by_name_or_id(ctx.guild.roles, guild_settings.default_role)

                            self.db.set_guild_category_settings(guildId=guild_id, categoryId=category.id, channelLimit=defaultLimit, channelLocked=locked, bitrate=defaultBitrate, defaultRole=(selected_guild_role or ctx.guild.default_role).id)
                        else:
                            self.log.debug(guild_id, _method , f"GUILD CATEGORY SETTINGS FOUND")
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_setup'), f"{ctx.author.mention}, {self.get_string(guild_id, 'ready_to_go')}", delete_after=10)
                    except Exception as e:
                        self.log.error(guild_id, _method, str(e), traceback.format_exc())
                        # traceback.print_exc()
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_setup'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_setup_error')}", delete_after=5)
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_setup'), f"{ctx.author.mention}, {self.get_string(guild_id, 'setup_no_permission')}", delete_after=10)
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=['get-default-role', 'gdr'])
    async def get_default_role(self, ctx):
        guild_id = ctx.guild.id
        _method = inspect.stack()[1][3]
        author = ctx.author
        try:
            if self.isAdmin(ctx):
                if self.isInVoiceChannel(ctx):
                    voice_channel = ctx.author.voice.channel
                    # category_id = ctx.author.voice.channel.category.id
                    self.db.open()
                    user_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel.id)
                    default_role = self.db.get_default_role(guildId=guild_id, categoryId=voice_channel.category.id, userId=user_id)
                    if default_role:
                        role = self.get_by_name_or_id(ctx.guild.roles, default_role)
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_settings'), f"{author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_get_default_role'), role=role.name)}", fields=None, delete_after=30)
                    else:
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_settings'), f"{author.mention}, {self.get_string(guild_id, 'info_default_role_not_found')}", fields=None, delete_after=5)
                else:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_permission_denied"), f"{author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
                self.log.debug(guild_id, _method , f"{ctx.author.mention} attempted to call get_default_role")
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            await ctx.message.delete()
            self.db.close()

    @voice.command(aliases=['set-default-role', 'sdr'])
    async def set_default_role(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        author = ctx.author
        if self.isAdmin(ctx):
            self.db.open()
            try:
                selected_default_role = await self.ask_default_role(ctx, self.get_string(guild_id, "title_voice_channel_settings"))
                if not selected_default_role:
                        selected_default_role = ctx.guild.default_role
                category = await self.set_role_ask_category(ctx)
                if category:
                    category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category.id)
                    if category_settings:
                        self.db.set_default_role_for_category(guildId=guild_id, categoryId=category.id, defaultRole=selected_default_role.id)
                    else:
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_voice_channel_settings"), f"{author.mention}, {self.get_string(guild_id, 'info_no_category_settings')}", fields=None, delete_after=5)
                else:
                    self.log.debug(guild_id, _method , f"unable to locate the expected category")
            except Exception as ex:
                self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            finally:
                self.db.close()
                await ctx.message.delete()

    @voice.command()
    async def settings(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        author = ctx.author
        if self.isAdmin(ctx):
            self.db.open()
            try:
                found_category = await self.set_role_ask_category(ctx)

                if found_category:
                    bitrate_value = await self.ask_bitrate(ctx, title=self.get_string(guild_id, "title_voice_channel_settings"))
                    locked = await self.ask_yes_no(ctx, question=self.get_string(guild_id, 'ask_default_locked'), title=self.get_string(guild_id, "title_voice_channel_settings"))
                    limit = await self.ask_limit(ctx, self.get_string(guild_id, "title_voice_channel_settings"))
                    new_default_role = await self.ask_default_role(ctx, self.get_string(guild_id, "title_voice_channel_settings"))
                    if not new_default_role:
                        new_default_role = ctx.guild.default_role

                    self.db.set_guild_category_settings(guildId=guild_id, categoryId=found_category.id, channelLimit=limit, channelLocked=locked, bitrate=bitrate_value, defaultRole=new_default_role.id)
                    embed_fields = list()
                    embed_fields.append({
                        "name": self.get_string(guild_id, 'locked'),
                        "value": str(locked)
                    })
                    embed_fields.append({
                        "name": self.get_string(guild_id, 'limit'),
                        "value": str(limit)
                    })
                    embed_fields.append({
                        "name": self.get_string(guild_id, 'bitrate'),
                        "value": f"{str(bitrate_value)}kbps"
                    })
                    embed_fields.append({
                        "name": self.get_string(guild_id, 'default_role'),
                        "value": f"{new_default_role.name}"
                    })

                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_voice_channel_settings"), f"{author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_category_settings'), category=found_category.name)}", fields=embed_fields, delete_after=5)

                else:
                    self.log.error(guild_id, _method, f"No Category found for '{found_category}'")
            except Exception as ex:
                self.log.error(guild_id, _method, str(ex), traceback.format_exc())
                await self.notify_of_error(ctx)
            finally:
                self.db.close()
        else:
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_voice_channel_settings"), f"{author.mention}, {self.get_string(guild_id, 'setup_no_permission')}", delete_after=5)
        await ctx.message.delete()

    @voice.command()
    async def cleandb(self,ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        author = ctx.author
        try:
            if self.isAdmin(ctx):
                self.db.open()
                self.db.clean_guild_user_settings(guildId=guild_id)
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_cleandb"), f"{author.mention}, {self.get_string(guild_id, 'info_cleandb')}", delete_after=5)
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_permission_denied"), f"{author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)

        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def reset(self,ctx, user: discord.Member = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            author = ctx.author
            if user and self.isAdmin(ctx):
                author = user
            self.db.clean_user_settings(guildId=guild_id, userId=author.id)
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_reset_user"), f"{author.mention}, {self.get_string(guild_id, 'info_reset_user')}", delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def lock(self, ctx, role: discord.Role = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        author = ctx.author
        try:
            owner_id = ctx.author.id
            owner = ctx.author
            category_id = ctx.author.voice.channel.category.id
            current_voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                current_voice_channel = ctx.author.voice.channel
                current_voice_channel_id = current_voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return

            if self.isAdmin(ctx):
                owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=current_voice_channel_id)
                owner = await self.get_or_fetch_user(owner_id)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)

            validRole = len([ x for x in ctx.guild.roles if x.name == default_role or x.id == default_role ]) == 1
            if not validRole:
                default_role = ctx.guild.default_role.id
            owned_channel_ids = self.db.get_tracked_voice_channel_id_by_owner(guildId=guild_id,ownerId=owner_id)
            is_owner = len([ c for c in owned_channel_ids if int(c) == current_voice_channel_id ]) >= 1
            if not is_owner and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_lock"), f'{author.mention}, {self.get_string(guild_id, "info_not_owner")}', delete_after=5)
            else:
                everyone = self.get_by_name_or_id(ctx.guild.roles, default_role)
                text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=current_voice_channel_id)
                if text_channel_id:
                    text_channel = await self.get_or_fetch_channel(text_channel_id)
                    if text_channel:
                        await text_channel.set_permissions(owner, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                        if everyone:
                            await text_channel.set_permissions(everyone, read_messages=False,send_messages=False, view_channel=True, read_message_history=False)

                    await current_voice_channel.set_permissions(owner, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    await current_voice_channel.set_permissions(everyone, connect=False, view_channel=True, stream=False)
                    if role:
                        await current_voice_channel.set_permissions(role, connect=False, read_messages=False, send_messages=False, view_channel=True, stream=False)
                        if text_channel:
                            await text_channel.set_permissions(role, read_messages=False,send_messages=False, view_channel=True, read_message_history=False)

                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_lock"), f'{author.mention}, Voice chat locked! 🔒', delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def unlock(self, ctx, role: discord.Role = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        author = ctx.author
        try:
            owner_id = ctx.author.id
            owner = ctx.author
            category_id = ctx.author.voice.channel.category.id
            current_voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                current_voice_channel = ctx.author.voice.channel
                current_voice_channel_id = current_voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return

            if self.isAdmin(ctx):
                owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=current_voice_channel_id)
                owner = await self.get_or_fetch_user(owner_id)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)

            validRole = len([ x for x in ctx.guild.roles if x.name == default_role or x.id == default_role ]) == 1
            if not validRole:
                default_role = ctx.guild.default_role.id
            owned_channel_ids = self.db.get_tracked_voice_channel_id_by_owner(guildId=guild_id,ownerId=owner_id)
            is_owner = len([ c for c in owned_channel_ids if int(c) == current_voice_channel_id ]) >= 1
            if not is_owner and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
            else:
                # everyone = discord.utils.get(ctx.guild.roles, name=default_role)
                everyone = self.get_by_name_or_id(ctx.guild.roles, default_role)
                text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=current_voice_channel_id)
                if text_channel_id:
                    text_channel = await self.get_or_fetch_channel(text_channel_id)

                    if text_channel:
                        await text_channel.set_permissions(owner, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                        if everyone:
                            await text_channel.set_permissions(everyone, read_messages=True,send_messages=True, view_channel=True, read_message_history=True)

                    await current_voice_channel.set_permissions(owner, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    await current_voice_channel.set_permissions(everyone, connect=True, view_channel=True, stream=True)
                    if role:
                        await current_voice_channel.set_permissions(role, connect=True, read_messages=True, send_messages=True, view_channel=True, stream=True)
                        if text_channel:
                            await text_channel.set_permissions(role, read_messages=True,send_messages=True, view_channel=True, read_message_history=True)

                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_channel_unlock'), f'{author.mention}, {self.get_string(guild_id, "info_unlocked")}', delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["allow"])
    async def permit(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_id = ctx.guild.id
        voice_channel_id = None
        text_channel = None
        if self.isInVoiceChannel(ctx):
            voice_channel = ctx.author.voice.channel
            voice_channel_id = voice_channel.id
        else:
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if not self.isAdmin(ctx) and ctx.author.id != owner_id:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
                return
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            if text_channel:
                if userOrRole:
                    await text_channel.set_permissions(userOrRole, read_messages=True, send_messages=True, view_channel=True, read_message_history=True, )
            if userOrRole:
                await voice_channel.set_permissions(userOrRole, connect=True, view_channel=True, speak=True, stream=True)
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_grant"), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_channel_grant"), user=userOrRole.name)}', delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_id = ctx.guild.id
        voice_channel_id = None
        text_channel = None
        voice_channel = None
        if self.isInVoiceChannel(ctx):
            voice_channel = ctx.author.voice.channel
            voice_channel_id = voice_channel.id
        else:
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if not self.isAdmin(ctx) and ctx.author.id != owner_id:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
                return
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            if userOrRole:
                await text_channel.set_permissions(userOrRole, read_messages=False, send_messages=False, view_channel=True, read_message_history=False)

            if userOrRole:
                for m in voice_channel.members:
                    if m.id != owner_id:
                        if m.id == userOrRole.id:
                            m.disconnect()
                        if m.has_role(userOrRole):
                            m.disconnect()

            await voice_channel.set_permissions(userOrRole, connect=False, read_messages=False, view_channel=True, speak=False, stream=False, read_message_history=False)
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_revoke"), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_channel_revoke"), user=userOrRole.name)}', delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def limit(self, ctx, limit):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            self.db.open()
            author = ctx.author
            owner = ctx.author
            owner_id = owner.id
            category_id = ctx.author.voice.channel.category.id

            channel_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = owner.voice.channel
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if self.isAdmin(ctx) or owner_id == author.id:
                owner = await self.get_or_fetch_user(owner_id)
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
                return

            await voice_channel.edit(user_limit=limit)
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_limit"), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_channel_limit"), limit=str(limit))}', delete_after=5)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id) or ctx.guild.default_role
            temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role)
            user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
            category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
            if user_settings:
                self.db.update_user_limit(guildId=guild_id, userId=owner_id, channelLimit=limit)
            else:
                self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=voice_channel.name, channelLimit=limit, bitrate=category_settings.bitrate, defaultRole=temp_default_role.id, autoGame=False)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def bitrate(self, ctx, bitrate: int = 64):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            self.db.open()
            author = ctx.author
            owner = ctx.author
            owner_id = owner.id
            category_id = ctx.author.voice.channel.category.id
            bitrate_min = 8
            bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))

            voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = owner.voice.channel
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if self.isAdmin(ctx) or owner_id == author.id:
                owner = await self.get_or_fetch_user(owner_id)
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
                return
            br_set = int(bitrate)

            if br_set > bitrate_limit:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_bitrate"), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_bitrate_too_high'), bitrate_max=bitrate_limit)}", delete_after=5)
                br_set = bitrate_limit
            elif br_set < bitrate_min:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_bitrate"), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_bitrate_too_high'), bitrate_min=bitrate_min)}", delete_after=5)
                br_set = bitrate_min

            br = br_set * 1000
            await voice_channel.edit(bitrate=br)
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_channel_bitrate"), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_bitrate_set"), bitrate=br_set)}', delete_after=5)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
            category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
            if user_settings:
                self.db.update_user_bitrate(guildId=guild_id, userId=owner_id, bitrate=br_set)
            else:
                self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=voice_channel.name, channelLimit=category_settings.channel_limit, bitrate=br_set, defaultRole=temp_default_role.id, autoGame=False)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["enable-auto-game", "eag"])
    async def auto_game(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            author = ctx.author
            owner_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = author.voice.channel
                channel_category_id = voice_channel.category.id
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id != author.id:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
                return

            enable_auto = await self.ask_yes_no(ctx, self.get_string(guild_id, "ask_enabled_auto_game"), self.get_string(guild_id, "title_enable_auto_game"))

            user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=channel_category_id, userId=owner_id)
            temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role)
            if temp_default_role is None:
                temp_default_role = ctx.guild.default_role
            if user_settings:
                self.db.set_user_settings_auto_game(guildId=guild_id, userId=owner_id, autoGame=enable_auto)
            else:
                self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=voice_channel.name, channelLimit=0, bitrate=self.settings.BITRATE_DEFAULT, defaultRole=temp_default_role.id, autoGame=enable_auto)
            state = self.get_string(guild_id, "disabled")
            if enable_auto:
                state = self.get_string(guild_id, "enabled")
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_enable_auto_game"), f'{author.mention}, {utils.str_replace(self.get_string(guild_id, "info_enable_auto_game"), state=state)}', delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    # "game": {
	#     "help": "**Change your channel name to the game you are currently playing**",
	# 	"usage": ".voice game",
	# 	"example": ".voice game",
	# 	"admin": false,
	# 	"aliases": []
	# },
    @voice.command()
    async def game(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        def check_user(m):
            return m.author.id == ctx.author.id
        try:
            author = ctx.author
            author_id = author.id
            channel_id = None
            selected_title = None
            if self.isInVoiceChannel(ctx):
                channel_id = ctx.author.voice.channel.id
            else:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=channel_id)
            if owner_id != author_id and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
                return
            owner = await self.get_or_fetch_member(ctx.guild, owner_id)
            if owner:
                selected_title = await self.ask_game_for_user(targetChannel=ctx.channel, user=owner, title=self.get_string(guild_id, "title_update_to_game"))
                if selected_title:
                    await self._name(ctx, selected_title, False)
                else:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_unknown_game"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_unknown_game")}', delete_after=5)
                    await ctx.message.delete()
            else:
                self.log.debug(guild_id, _method, f"Unable to locate the owner for 'game' call.")
                await ctx.message.delete()
        except discord.errors.NotFound as nf:
            self.log.warn(guild_id, _method, str(nf), traceback.format_exc())
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)

    @voice.command()
    async def name(self, ctx, *, name: str = None):
        await self._name(ctx, name=name, saveSettings=True)

    async def _name(self, ctx, name: str = None, saveSettings: bool = True):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        voice_channel_id = None
        voice_channel = None
        if self.isInVoiceChannel(ctx):
            voice_channel_id = ctx.author.voice.channel.id
            voice_channel = ctx.author.voice.channel
        else:
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
            return
        if not name or name == "":
            name = utils.get_random_name()
        self.db.open()
        author_id = ctx.author.id
        category_id = ctx.author.voice.channel.category.id
        try:
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id != author_id and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
                return
            category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            is_tracked_channel = len([c for c in self.db.get_tracked_voice_channel_id_by_owner(guildId=guild_id, ownerId=owner_id) if c == voice_channel_id]) >= 1
            if not is_tracked_channel:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_update_channel_name'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_voice_not_tracked')}", delete_after=5)
                return

            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(int(text_channel_id))
            if text_channel:
                await text_channel.edit(name=name)

            await voice_channel.edit(name=name)
            if saveSettings:
                user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
                if user_settings:
                    self.db.update_user_channel_name(guildId=guild_id, userId=owner_id, channelName=name)
                else:
                    self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=name, channelLimit=category_settings.channel_limit, bitrate=category_settings.bitrate, defaultRole=temp_default_role.id, autoGame=False)
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_update_channel_name'), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_channel_name_change"), channel=name)}', delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["rename"])
    async def force_name(self, ctx, *, name: str = None):
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_id = ctx.guild.id
        channel_id = ctx.author.voice.channel.id
        channel = ctx.author.voice.channel
        try:
            if not self.isInVoiceChannel(ctx):
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return
            if self.isAdmin(ctx):
                if not name or name == "":
                    name = utils.get_random_name()
                category_id = ctx.author.voice.channel.category.id
                guild_category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
                owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=channel_id)
                if not owner_id:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_update_channel_name'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_voice_not_tracked')}", delete_after=5)
                    return
                user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
                default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
                temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
                # text channel rename is automatically handled by the change event on the voice channel.

                if channel:
                    self.log.debug(guild_id, _method, f"Edit the channel to: {channel.name} -> {name}")
                    await channel.edit(name=name)
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_update_channel_name'), f'{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, "info_channel_name_change"), channel=name)}', delete_after=5)

                if user_settings:
                    self.db.update_user_channel_name(guildId=guild_id, userId=owner_id, channelName=name)
                else:
                    self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=name, channelLimit=guild_category_settings.channel_limit, bitrate=guild_category_settings.bitrate, defaultRole=temp_default_role.id, autoGame=False)
            else:
                self.log.debug(guild_id, _method, f"{ctx.author} tried to run command 'rename'")
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def whoowns(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            self.db.open()
            channel = ctx.author.voice.channel
            if channel == None:
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
            else:
                owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=channel.id)
                if owner_id:
                    owner = await self.get_or_fetch_member(ctx.guild, owner_id)
                    if owner:
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_who_owns'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_who_owns'), channel=channel.name, user=owner.mention)}", delete_after=30)
                    else:
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_who_owns'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_who_owns'), channel=channel.name, user=f'UserId:{str(owner_id)}')}", delete_after=30)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def give(self, ctx, newOwner: discord.Member):
        """Give ownership of the channel to another user in the channel"""
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_id = ctx.guild.id
        if not self.isInVoiceChannel(ctx):
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_not_in_channel'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
            return
        try:
            channel = ctx.author.voice.channel
            channel_id = ctx.author.voice.channel.id
            new_owner_id = newOwner.id
            # update_tracked_channel_owner
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=channel_id)
            if new_owner_id == owner_id:
                # Can't grant to self
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_update_owner'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_channel_owned_you')}", delete_after=5)
            else:
                self.db.update_tracked_channel_owner(guildId=guild_id, voiceChannelId=channel_id, ownerId=owner_id, newOwnerId=new_owner_id)
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_update_owner'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_new_owner'), user=newOwner.mention)}", delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def claim(self, ctx):
        _method = inspect.stack()[1][3]
        found_as_owner = False
        self.db.open()
        guild_id = ctx.guild.id
        if not self.isInVoiceChannel(ctx):
            await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_not_in_channel'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
            return
        try:
            channel = ctx.author.voice.channel
            aid = ctx.author.id

            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=channel.id)
            if not owner_id and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_permission_denied'), f"{ctx.author.mention}, {self.get_string(guild_id, 'info_permission_denied')}", delete_after=5)
            else:
                for data in channel.members:
                    if data.id == owner_id:
                        owner = await self.get_or_fetch_member(ctx.guild, owner_id)
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_update_owner'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_channel_owned'), user=owner.mention)}", delete_after=5)
                        found_as_owner = True
                        break
                if not found_as_owner:
                    self.db.update_tracked_channel_owner(guildId=guild_id, voiceChannelId=channel.id, ownerId=owner_id, newOwnerId=aid)
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_update_owner'), f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_new_owner'), user=ctx.author.mention)}", delete_after=5)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    async def ask_yes_no(self, ctx, question: str, title: str = "Voice Channel Setup"):
        guild_id = ctx.guild.id
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        buttons = [
            create_button(style=ButtonStyle.green, label=self.get_string(guild_id, 'yes'), custom_id="YES"),
            create_button(style=ButtonStyle.red, label=self.get_string(guild_id, 'no'), custom_id="NO")
        ]
        yes_no = False
        action_row = create_actionrow(*buttons)
        yes_no_req = await self.sendEmbed(ctx.channel, title, question, components=[action_row], delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
        else:
            yes_no = utils.str2bool(button_ctx.custom_id)
            await yes_no_req.delete()
        return yes_no

    async def ask_limit(self, ctx, title: str = "Voice Channel Setup"):
        guild_id = ctx.guild.id
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        def check_numeric(m):
            if check_user(m):
                if m.content.isnumeric():
                    val = int(m.content)
                return val >= 0 and val <= 100
            return False

        defaultLimit = 0

        limit_ask = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_limit'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
        try:
            limitResp = await self.bot.wait_for('message', check=check_numeric, timeout=60)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
            return
        else:
            defaultLimit = int(limitResp.content)
            await limitResp.delete()
            await limit_ask.delete()
        return defaultLimit

    async def ask_bitrate(self, ctx, title: str = "Voice Channel Setup"):
        guild_id = ctx.guild.id
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        def check_bitrate(m):
            if check_user(m):
                if m.content.isnumeric():
                    bitrate_min = 8
                    bitrate_limit = int(round(m.guild.bitrate_limit / 1000))
                    set_br = int(m.content)
                    return set_br == 0 or (set_br >= bitrate_min and set_br <= bitrate_limit)
                return False

        # ASK SET DEFAULT BITRATE
        defaultBitrate = 64

        bitrate_min = 8
        bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))
        bitrate_ask = await self.sendEmbed(ctx.channel, title, f'{utils.str_replace(self.get_string(guild_id, "info_bitrate"), bitrate_min=str(bitrate_min), bitrate_limit=str(bitrate_limit))}', delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
        try:
            bitrateResp = await self.bot.wait_for('message', check=check_bitrate, timeout=60)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
            return
        else:
            defaultBitrate = int(bitrateResp.content)
            await bitrateResp.delete()
            await bitrate_ask.delete()
            if defaultBitrate == 0:
                defaultBitrate = self.settings.BITRATE_DEFAULT
        return defaultBitrate

    async def set_role_ask_category(self, ctx, title: str = "Set Default Role"):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        if not self.isAdmin(ctx):
            raise PermissionError()
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same

        options = []
        categories = [r for r in ctx.guild.categories]
        categories.sort(key=lambda r: r.name)
        options.append(create_select_option(label=self.get_string(guild_id, 'new'), value="-1", emoji="⭐"))
        options.append(create_select_option(label=self.get_string(guild_id, 'other'), value="0", emoji="⏭"))
        sub_message = self.get_string(guild_id, 'ask_category_submessage')
        for r in categories[:23]:
            options.append(create_select_option(label=r.name, value=str(r.id), emoji="📇"))

        select = create_select(
            options=options,
            placeholder=self.get_string(guild_id, 'placeholder_category'),
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )

        action_row = create_actionrow(select)
        ask_context = await self.sendEmbed(ctx.channel, title, f"{self.get_string(guild_id, 'ask_category')} {sub_message}", delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'), components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, "took_too_long"), delete_after=5)
        else:
            category_id = int(button_ctx.selected_options[0])
            await ask_context.delete()
            if category_id == 0: # selected "OTHER"
                try:
                    ask_existing_category = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_category_name'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
                    category = await self.bot.wait_for('message', check=check_user, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, "took_too_long"), delete_after=5)
                else:
                    await ask_existing_category.delete()
                    cat_name_or_id = category.content
                    if cat_name_or_id.isnumeric():
                        cat_name_or_id = int(cat_name_or_id)
                    found_category = self.get_by_name_or_id(ctx.guild.categories, cat_name_or_id)
                    await category.delete()
                    if found_category:
                        await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_found_existing_category'), category=found_category.name)}", delete_after=5)
                        return found_category
                    else:
                        await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_no_category_found'), category=found_category.name)}", delete_after=5)
                        return None
            elif category_id == -1: # selected "NEW"
                try:
                    ask_new_category = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_new_category_name'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
                    new_category = await self.bot.wait_for('message', check=check_user, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, "took_too_long"), delete_after=5)
                else:
                    await ask_new_category.delete()
                    selected_category = await ctx.guild.create_category_channel(new_category.content)
                    await new_category.delete()
                    await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_category_created'), category=selected_category.name)}", delete_after=5)

                    return selected_category
            else: # selected a category
                selected_category = discord.utils.get(ctx.guild.categories, id=category_id)
                if selected_category:
                    self.log.debug(guild_id, _method, f"{ctx.author.mention} selected the category '{selected_category.name}'")
                    await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_category_selected'), category=selected_category.name)}", delete_after=5)
                    return selected_category
                else:
                    await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {self.get_string(guild_id, 'info_unverified_category')}", delete_after=5)
                    return None

    async def ask_game_for_user(self, targetChannel: discord.TextChannel, user: discord.Member, title: str):
        def check_user(m):
            same = m.author.id == user.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = targetChannel.guild.id
        options = []
        games = []

        if user.activities:
            game_activity = [a for a in user.activities if a.type == discord.ActivityType.playing]
            stream_activity = [a for a in user.activities if a.type == discord.ActivityType.streaming]
            watch_activity = [a for a in user.activities if a.type == discord.ActivityType.watching]

            for a in game_activity:
                if a.name not in games:
                    self.log.debug(guild_id, _method, f"game.name: {a.name}")
                    games.append(a.name)
            for a in stream_activity:
                self.log.debug(guild_id, _method, f"stream.game: {a.game}")
                self.log.debug(guild_id, _method, f"stream.name: {a.name}")
                if a.game not in games:
                    games.append(a.game)
                if a.name not in games:
                    games.append(a.name)
            for a in watch_activity:
                self.log.debug(guild_id, _method, f"watch.name: {a.name}")
                if a.name not in games:
                    games.append(a.name)
            # for a in user.activities:
            #     self.log.debug(guild_id, _method, f"activity.name: {a.name}")
            #     if a.name not in games:
            #         games.append(a.name)

            if len(games) == 1:
                return games[0]
            elif len(games) == 0:
                return None


            if len(games) >= 24:
                self.log.warn(user.guild.id, _method, f"There are more than 24 games: {str(len(user))}")
            for g in games[:24]:
                options.append(create_select_option(label=g, value=g, emoji="🎮"))

            select = create_select(
                options=options,
                placeholder=self.get_string(guild_id, 'placeholder_game'),
                min_values=1, # the minimum number of options a user must select
                max_values=1 # the maximum number of options a user can select
            )

            action_row = create_actionrow(select)
            ask_context = await self.sendEmbed(targetChannel, title, self.get_string(guild_id, 'ask_multiple_games'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'), components=[action_row])
            try:
                button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=60.0)
            except asyncio.TimeoutError:
                await self.sendEmbed(targetChannel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
            else:
                await ask_context.delete()
                selected_game = button_ctx.selected_options[0]
                if selected_game:
                    await self.sendEmbed(targetChannel, title, f"{user.mention}, {utils.str_replace(self.get_string(guild_id, 'info_game_selected'), game=selected_game.name)}", delete_after=5)
                    return selected_game
                else:
                    return None
        else:
            return None

    async def ask_role_by_name_or_id(self, ctx, title: str = "Voice Channel Initialization"):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        role_id = None
        try:
            ask_role_name_id = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_role_name_or_id'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
            role_name_id_resp = await self.bot.wait_for('message', check=check_user, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, "took_too_long"), delete_after=5)
        else:
            await ask_role_name_id.delete()
            role_name_id = role_name_id_resp.content
            if role_name_id.isnumeric():
                role_name_id = int(role_name_id)
            found_role= self.get_by_name_or_id(ctx.guild.roles, role_name_id)
            await role_name_id_resp.delete()
            if found_role:
                role_id = found_role.id
            else:
                await self.sendEmbed(ctx.channel, title, utils.str_replace(self.get_string(guild_id, "info_role_not_found"), role=str(role_name_id)), delete_after=5)
                role_id = ctx.guild.default_role.id
        return role_id

    async def ask_admin_role(self, ctx, title: str = "Voice Channel Initialization"):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        options = []
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and not r.managed and not r.is_integration() and r.permissions.administrator]
        roles.sort(key=lambda r: r.name)
        sub_message = ""
        if len(roles) >= 24:
            self.log.warn(ctx.guild.id, _method, f"Guild has more than 24 roles. Total Roles: {str(len(roles))}")
            options.append(create_select_option(label=self.get_string(guild_id, 'other'), value="0", emoji="⏭"))
            sub_message = self.get_string(guild_id, 'ask_admin_role_submessage')
        for r in roles[:24]:
            options.append(create_select_option(label=r.name, value=str(r.id), emoji="🏷"))

        select = create_select(
            options=options,
            placeholder=self.get_string(guild_id, 'placeholder_admin_role'),
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )

        action_row = create_actionrow(select)
        ask_context = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_admin_role'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'), components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
        else:
            role_id = int(button_ctx.selected_options[0])
            if role_id == 0:
                role_id = await self.ask_role_by_name_or_id(ctx, title)

            await ask_context.delete()
            selected_role = discord.utils.get(ctx.guild.roles, id=role_id)
            if selected_role:
                self.log.debug(guild_id, _method, f"{ctx.author.mention} selected the role '{selected_role.name}'")
                await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_role_selected'), role=selected_role.name)}", delete_after=5)
                return selected_role
            else:
                await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {self.get_string(guild_id, 'info_unverified_admin_role')}", delete_after=5)
                return None

    async def ask_default_role(self, ctx, title: str = "Voice Channel Setup"):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        options = []
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and not r.managed and not r.is_integration()]
        roles.sort(key=lambda r: r.name)
        if len(roles) >= 24:
            self.log.warn(ctx.guild.id, _method, f"Guild has more than 24 roles. Total Roles: {str(len(roles))}")
            options.append(create_select_option(label=self.get_string(guild_id, 'other'), value="0", emoji="⏭"))
        for r in roles[:24]:
            options.append(create_select_option(label=r.name, value=str(r.id), emoji="🏷"))

        select = create_select(
            options=options,
            placeholder=self.get_string(guild_id, 'placeholder_default_role'),
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )

        action_row = create_actionrow(select)
        ask_context = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_default_role'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'), components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
        else:
            role_id = int(button_ctx.selected_options[0])
            if role_id == 0:
                role_id = await self.ask_role_by_name_or_id(ctx, title)

            await ask_context.delete()
            selected_role = discord.utils.get(ctx.guild.roles, id=role_id)
            if selected_role:
                self.log.debug(guild_id, _method, f"{ctx.author.mention} selected the role '{selected_role.name}'")
                await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_role_selected'), role=selected_role.name)}", delete_after=5)
                return selected_role
            else:
                await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {self.get_string(guild_id, 'info_unverified_role')}", delete_after=5)
                return None

    async def ask_category(self, ctx, title: str = "Voice Channel Setup"):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        options = []
        categories = [r for r in ctx.guild.categories]
        categories.sort(key=lambda r: r.name)
        options.append(create_select_option(label=self.get_string(guild_id, 'new'), value="-1", emoji="⭐"))
        options.append(create_select_option(label=self.get_string(guild_id, 'other'), value="0", emoji="⏭"))
        sub_message = self.get_string(guild_id, 'ask_category_submessage')
        for r in categories[:23]:
            options.append(create_select_option(label=r.name, value=str(r.id), emoji="📇"))

        select = create_select(
            options=options,
            placeholder=self.get_string(guild_id, 'placeholder_category'),
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )

        action_row = create_actionrow(select)
        ask_context = await self.sendEmbed(ctx.channel, title, f"{self.get_string(guild_id, 'ask_category')}{sub_message}", delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'), components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
        else:
            category_id = int(button_ctx.selected_options[0])
            await ask_context.delete()
            if category_id == 0: # selected "OTHER"
                try:
                    ask_existing_category = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_category_name'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
                    category = await self.bot.wait_for('message', check=check_user, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
                else:
                    await ask_existing_category.delete()
                    cat_name_or_id = category.content
                    if cat_name_or_id.isnumeric():
                        cat_name_or_id = int(cat_name_or_id)
                    found_category = self.get_by_name_or_id(ctx.guild.categories, cat_name_or_id)
                    await category.delete()
                    if found_category:
                        await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_found_existing_category'), category=found_category.name)}", delete_after=5)
                        return found_category
                    else:
                        await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_no_category_found'), category=cat_name_or_id)}", delete_after=5)
                        return None
            elif category_id == -1: # selected "NEW"
                try:
                    ask_new_category = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_new_category_name'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
                    new_category = await self.bot.wait_for('message', check=check_user, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
                else:
                    await ask_new_category.delete()
                    selected_category = await ctx.guild.create_category_channel(new_category.content)
                    await new_category.delete()
                    await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {self.get_string(guild_id, 'info_created_category')} '{selected_category.name}'", delete_after=5)

                    return selected_category
            else: # selected a category
                selected_category = discord.utils.get(ctx.guild.categories, id=category_id)
                if selected_category:
                    self.log.debug(guild_id, _method, f"{ctx.author.mention} selected the category '{selected_category.name}'")
                    await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, {self.get_string(guild_id, 'info_selected_category')} '{selected_category.name}'", delete_after=5)
                    return selected_category
                else:
                    await self.sendEmbed(ctx.channel, title, f'{ctx.author.mention}, {self.get_string(guild_id, "info_unverified_category")}', delete_after=5)
                    return None

    async def ask_language(self, ctx, title: str = "Voice Channel Setup"):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        options = []

        # lang_manifest = os.path.join(os.path.dirname(__file__), "../../languages/manifest.json")
        # manifest = {}
        # if os.path.exists(lang_manifest):
        #     with open(lang_manifest, encoding="UTF-8") as manifest_file:
        #         manifest.update(json.load(manifest_file))
        for l in self.settings.languages:
            options.append(create_select_option(label=self.settings.languages[l], value=l, emoji="🗣"))


        # lang_files = glob.glob(os.path.join(os.path.dirname(__file__), "../../languages", "[a-z][a-z]-[a-z][a-z].json"))
        # languages = [os.path.basename(f)[:-5] for f in lang_files if os.path.isfile(f)]
        # for r in languages[:23]:
            # options.append(create_select_option(label=r, value=r, emoji="🗣"))

        select = create_select(
            options=options,
            placeholder=self.get_string(guild_id, "placeholder_language"),
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )

        action_row = create_actionrow(select)
        language_id = self.settings.language
        ask_language = await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'ask_language'), delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'), components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
        else:
            language_id = button_ctx.selected_options[0]
            await ask_language.delete()
        return language_id

    def isInVoiceChannel(self, ctx):
        if isinstance(ctx, discord.Member):
            return ctx.voice.channel is not None
        else:
            return ctx.author.voice.channel is not None

    def isAdmin(self, ctx):
        _method = inspect.stack()[1][3]
        self.db.open()
        guild_settings = self.db.get_guild_settings(ctx.guild.id)
        is_in_guild_admin_role = False
        # see if there are guild settings for admin role
        if guild_settings:
            guild_admin_role = self.get_by_name_or_id(ctx.guild.roles, guild_settings.admin_role)
            is_in_guild_admin_role = guild_admin_role in ctx.author.roles
        is_bot_owner = str(ctx.author.id) == self.settings.bot_owner
        return is_bot_owner or is_in_guild_admin_role

    async def sendEmbed(self, channel, title, message, fields=None, delete_after=None, footer=None, components=None):
        embed = discord.Embed(title=title, description=message, color=0x7289da)
        if fields is not None:
            for f in fields:
                embed.add_field(name=f['name'], value=f['value'], inline='false')
        if footer is None:
            embed.set_footer(text=f'Developed by {self.settings.author}')
        else:
            embed.set_footer(text=footer)
        return await channel.send(embed=embed, delete_after=delete_after, components=components)

    async def notify_of_error(self, ctx):
        guild_id = ctx.guild.id
        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_error'), f'{ctx.author.mention}, {self.get_string(guild_id, "info_error")}', delete_after=30)

    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        if isinstance(nameOrId, str):
            return discord.utils.get(iterable, name=str(nameOrId))
        elif isinstance(nameOrId, int):
            return discord.utils.get(iterable, id=int(nameOrId))
        else:
            return None

    async def get_or_fetch_channel(self, channelId: int):
        _method = inspect.stack()[1][3]
        try:
            if channelId:
                chan = self.bot.get_channel(channelId)
                if not chan:
                    chan = await self.bot.fetch_channel(channelId)
                return chan
            else:
                return  None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_user(self, userId: int):
        _method = inspect.stack()[1][3]
        try:
            if userId:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_member(self, guild, userId: int):
        _method = inspect.stack()[1][3]
        try:
            if userId:
                user = guild.get_member(userId)
                if not user:
                    user = await guild.fetch_member(userId)
                return user
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    @setup.error
    async def info_error(self, ctx, error):
        _method = inspect.stack()[1][3]
        if isinstance(error, discord.errors.NotFound):
            self.log.warn(ctx.guild.id, _method , str(error), traceback.format_exc())
        else:
            self.log.error(ctx.guild.id, _method , str(error), traceback.format_exc())

    def set_guild_strings(self, guildId: int):
        _method = inspect.stack()[1][3]
        guild_settings = self.db.get_guild_settings(guildId)
        lang = self.settings.language
        if guild_settings:
            lang = guild_settings.language
        self.strings[str(guildId)] = self.settings.strings[lang]
        self.log.debug(guildId, _method, f"Guild Language Set: {lang}")

        # for x in self.strings[str(guildId)]:
        #     self.log.debug(guildId, _method, self.get_string(guildId, x))

    def get_string(self, guildId: int, key: str):
        _method = inspect.stack()[1][3]
        if not key:
            self.log.debug(guildId, _method, f"KEY WAS EMPTY")
            return ''
        if str(guildId) in self.strings:
            if key in self.strings[str(guildId)]:
                return self.strings[str(guildId)][key]
            elif key in self.settings.strings[self.settings.language]:
                self.log.debug(guildId, _method, f"Unable to find key in defined language. Falling back to {self.settings.language}")
                return self.settings.strings[self.settings.language][key]
            else:
                self.log.warn(guildId, _method, f"UNKNOWN STRING KEY: {key}")
                return f"{key}"
        else:
            if key in self.settings.strings[self.settings.language]:
                return self.settings.strings[self.settings.language][key]
            else:
                self.log.warn(guildId, _method, f"UNKNOWN STRING KEY: {key}")
                return f"{key}"

    def get_language(self, guildId: int):
        guild_setting = self.db.get_guild_settings(guildId)
        if not guild_setting:
            return self.settings.language
        return guild_setting.language or self.settings.language

async def setup(bot):
    await bot.add_cog(voice(bot))
