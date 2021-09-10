import discord
import math
import asyncio
import json
import datetime
from discord.ext import commands
import traceback
import sqlite3
from urllib.parse import quote
import validators
from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure
from time import gmtime, strftime
import os
import glob
import typing
from .lib import utils
from .lib import settings
# from .lib import sqlite
from .lib import mongo
class EmbedField():
    def __init__(self, name, value):
        self.name = name
        self.value = value

class voice(commands.Cog):
    def __init__(self, bot):
        self.settings = settings.Settings()
        self.bot = bot
        # self.db = sqlite.SqliteDatabase()
        self.db = mongo.MongoDatabase()

    async def clean_up_tracked_channels(self, guildID):
        print("Clean up tracked channels")
        self.db.open()
        try:

            print(f"checking guild create channels")
            guildSettings = self.db.get_guild_create_channel_settings(guildId=guildID)
            if guildSettings and guildSettings.channels:
                for cc in guildSettings.channels:
                    cc_channel = await self.get_or_fetch_channel(cc.channel_id)
                    if not cc_channel:
                        # delete this channel as it no longer exists.
                        print(f"Deleting create channel {cc.channel_id} as it does not exist")
                        self.db.delete_guild_create_channel(guildId=guildID, channelId=cc.channel_id, categoryId=cc.category_id)
                        pass

            print(f"checking user created channels")
            trackedChannels = self.db.get_tracked_voice_channel_ids(guildID)
            for vc in trackedChannels:
                textChannel = None
                voiceChannelId = vc
                if voiceChannelId:
                    voiceChannel = await self.get_or_fetch_channel(voiceChannelId)

                    textChannelId = self.db.get_text_channel_id(guildID, voiceChannelId)
                    if textChannelId:
                        textChannel = await self.get_or_fetch_channel(textChannelId)

                    if voiceChannel:
                        if len(voiceChannel.members) == 0 and len(voiceChannel.voice_states) == 0:
                            print(f"Start Tracked Cleanup: {voiceChannelId}")
                            print(f"Deleting Channel {voiceChannel} because everyone left")
                            self.db.clean_tracked_channels(guildID, voiceChannelId, textChannelId)
                            if textChannel:
                                await textChannel.delete()
                            await voiceChannel.delete()
                    else:
                        print(f"Unable to find voice channel: {voiceChannelId}")
                        self.db.clean_tracked_channels(guildID, voiceChannelId, textChannelId)
        except discord.errors.NotFound as nf:
            print(nf)
            traceback.print_exc()
            print("Channel Not Found. Already Cleaned Up")
        finally:
             self.db.close()

    @commands.group()
    async def voice(self, ctx):
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.clean_up_tracked_channels(guild.id)


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild_id = after.guild.id
        if not after:
            pass
        is_in_channel = after is not None and after.voice is not None and after.voice.channel is not None
        if is_in_channel:
            print(f"[on_member_update] Member Update Start of user: '{after.name}'")
            voice_channel = after.voice.channel
            voice_channel_id = voice_channel.id
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id != after.id:
                # user is in a channel, but not their channel
                print("[on_member_update] User is in a channel, but not their own channel.")
                pass
            if before.activity == after.activity:
                # we are only looking at activity
                print("[on_member_update] Before / After activity is the same")
                pass

            owner = await self.get_or_fetch_member(owner_id)
            user_settings = self.db.get_user_settings(guild_id, after.id)
            if user_settings and user_settings.auto_game:
                print(f"[on_member_update] trigger auto game change")
                channel_name = voice_channel.name
                if owner.activities:
                    game_activity = [a for a in owner.activities if a.type == discord.ActivityType.playing]
                    stream_activity = [a for a in owner.activities if a.type == discord.ActivityType.streaming]
                    watch_activity = [a for a in owner.activities if a.type == discord.ActivityType.watching]
                    if game_activity:
                        if len(game_activity) > 1:
                            print(f"[on_member_update] There are multiple choices. Ask?")
                            channel_name = game_activity[0].name
                            pass
                        else:
                            channel_name = game_activity[0].name
                    elif stream_activity:
                        channel_name = stream_activity[0].game
                    elif watch_activity:
                        channel_name = watch_activity[0].name
                if voice_channel.name != channel_name:
                    text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
                    if text_channel_id:
                        text_channel = await self.get_or_fetch_channel(int(text_channel_id))
                    if text_channel:
                        print(f"[on_member_update] Change Text Channel Name: {channel_name}")
                        await text_channel.edit(name=channel_name)
                        await self.sendEmbed(text_channel, "Updated Channel Name", f'{after.mention}, You have changed the channel name to {channel_name}!', delete_after=5)
                    voice_channel.edit(name=channel_name)
            else:
                print(f"[on_member_update] trigger name change, but setting is false.")
        pass

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        self.db.open()
        try:
            if before and after:
                if before.id == after.id:
                    # This handles a manual channel rename. it changes the text channel name to match.
                    guildID = before.guild.id or after.guild.id
                    channel = await self.get_or_fetch_channel(after.id)
                    category_id = before.category.id or after.category.id or channel.category.id
                    channelOwnerId = self.db.get_channel_owner_id(guildID, after.id)
                    if channelOwnerId:
                        if before.name == after.name:
                            # same name. ignore
                            print(f"[on_guild_channel_update] Channel Names are the same. Nothing to do")
                            pass
                        else:
                            userSettings = self.db.get_user_settings(guildID, channelOwnerId)
                            guildSettings = self.db.get_guild_category_settings(guildId=guildID, categoryId=category_id)

                            if userSettings:
                                default_role = self.get_by_name_or_id(after.guild.roles, userSettings.default_role)
                            else:
                                if guildSettings:
                                    default_role = self.get_by_name_or_id(after.guild.roles, guildSettings.default_role or self.settings.default_role)
                                else:
                                    default_role = self.get_by_name_or_id(after.guild.roles, self.settings.default_role or "@everyone")
                            print(f"[on_guild_channel_update] Channel Type: {after.type}")
                            if after.type == discord.ChannelType.voice:
                                # new channel name
                                text_channel_id = self.db.get_text_channel_id(guildId=guildID, voiceChannelId=after.id)
                                if text_channel_id:
                                    textChannel = await self.get_or_fetch_channel(int(text_channel_id))
                                if textChannel:
                                    print(f"[on_guild_channel_update] Change Text Channel Name: {after.name}")
                                    await textChannel.edit(name=after.name)
                                    await self.sendEmbed(textChannel, "Updated Channel Name", f'You have changed the channel name to {textChannel.name}!', delete_after=5)
                            if after.type == discord.ChannelType.text:
                                voiceChannel = None
                                voice_channel_id = self.db.get_voice_channel_id_from_text_channel(guildId=guildID, textChannelId=after.id)
                                if voice_channel_id:
                                    voiceChannel = await self.get_or_fetch_channel(voice_channel_id)
                                if voiceChannel:
                                    print(f"[on_guild_channel_update] change Voice Channel Name: {after.name}")
                                    await voiceChannel.edit(name=after.name)
                                    await self.sendEmbed(after, "Updated Channel Name", f'You have changed the channel name to {after.name}!', delete_after=5)


                            if userSettings:
                                self.db.update_user_channel_name(guildId=guildID, userId=channelOwnerId, channelName=after.name)
                            else:
                                self.db.insert_user_settings(guildId=guildID, userId=channelOwnerId, channelName=after.name, channelLimit=0, bitrate=self.settings.BITRATE_DEFAULT, defaultRole=default_role.id, autoGame=False)
        except Exception as e:
            print(e)
            traceback.print_exc()
        finally:
            self.db.close()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        self.db.open()
        print("[on_voice_state_update] On Voice State Update")
        guildID = member.guild.id
        await self.clean_up_tracked_channels(guildID)
        await asyncio.sleep(2)
        voiceChannels = self.db.get_guild_create_channels(guildID)
        if voiceChannels is None:
            print(f"[on_voice_state_update] No voice create channels found for GuildID: {guildID}")
            pass
        else:
            try:
                print("[on_voice_state_update] Check for user in Create Channel")
                if after.channel is not None and after.channel.id in voiceChannels:
                    # User Joined the CREATE CHANNEL
                    print(f"[on_voice_state_update] User requested to CREATE CHANNEL")
                    category_id = after.channel.category_id
                    source_channel_id = after.channel.id
                    userSettings = self.db.get_user_settings(guildId=guildID, userId=member.id)
                    guildSettings = self.db.get_guild_category_settings(guildId=guildID, categoryId=category_id)
                    useStage = self.db.get_use_stage_on_create(guildId=guildID, channelId=source_channel_id, categoryId=category_id) or 0
                    # CHANNEL SETTINGS START
                    limit = 0
                    locked = False
                    bitrate = self.settings.BITRATE_DEFAULT
                    stage = useStage >= 1
                    name = utils.get_random_name()

                    default_role = self.get_by_name_or_id(member.guild.roles, self.settings.default_role)
                    if userSettings is None:
                        if guildSettings is not None:
                            limit = guildSettings.channel_limit
                            locked = guildSettings.channel_locked
                            bitrate = guildSettings.bitrate
                            default_role = self.get_by_name_or_id(member.guild.roles, guildSettings.default_role or self.settings.default_role)
                    else:
                        name = userSettings.channel_name
                        if guildSettings is None:
                            limit = userSettings.channel_limit
                            bitrate = userSettings.bitrate
                            default_role = self.get_by_name_or_id(member.guild.roles, userSettings.default_role or self.settings.default_role)
                            locked = False
                        elif guildSettings is not None:
                            limit = userSettings.channel_limit or guildSettings.channel_limit
                            locked = guildSettings.channel_locked or False
                            bitrate = userSettings.bitrate or guildSettings.bitrate
                            default_role = self.get_by_name_or_id(member.guild.roles, userSettings.default_role or guildSettings.default_role or self.settings.default_role)
                        else:
                            limit = userSettings.channel_limit
                            locked = guildSettings.channel_locked
                            bitrate = guildSettings.bitrate
                            default_role = self.get_by_name_or_id(member.guild.roles, guildSettings.default_role or self.settings.default_role)
                    # CHANNEL SETTINGS END

                    mid = member.id
                    category = discord.utils.get(member.guild.categories, id=category_id)
                    print(f"[on_voice_state_update] Creating channel {name} in {category} with bitrate {bitrate}kbps")
                    is_community = member.guild.features.count("COMMUNITY") > 0
                    if(stage and is_community):
                        print(f"[on_voice_state_update] Creating Stage Channel")
                        stage_topic = utils.get_random_name(noun_count=1, adjective_count=2)
                        voiceChannel = await member.guild.create_stage_channel(name, topic=stage_topic, category=category, reason="Create Channel Request by {member}")
                    else:
                        print(f"[on_voice_state_update] Created Voice Channel")
                        voiceChannel = await member.guild.create_voice_channel(name, category=category, reason="Create Channel Request by {member}")
                    textChannel = await member.guild.create_text_channel(name, category=category)
                    channelID = voiceChannel.id

                    print(f"[on_voice_state_update] Moving {member} to {voiceChannel}")
                    await member.move_to(voiceChannel)
                    # if the bot cant do this, dont fail...
                    try:
                        print(f"[on_voice_state_update] Setting permissions on {voiceChannel}")
                        await voiceChannel.set_permissions(member, speak=True, priority_speaker=True, connect=True, read_messages=True, send_messages=True, view_channel=True, stream=True)
                        await textChannel.set_permissions(member, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    except Exception as ex:
                        print(ex)
                        traceback.print_exc()
                    print(f"[on_voice_state_update] Set user limit to {limit} on {voiceChannel}")
                    await voiceChannel.edit(name=name, user_limit=limit, bitrate=(bitrate*1000))
                    print(f"[on_voice_state_update] Track voiceChannel userID: {mid} channelID: {channelID}")
                    print(f"[on_voice_state_update] Track Voice and Text Channels {name} in {category}")

                    self.db.track_new_channel_set(guildId=guildID, ownerId=mid, voiceChannelId=channelID, textChannelId=textChannel.id)

                    sec_role = default_role or self.get_by_name_or_id(member.guild.roles, self.settings.default_role or "@everyone")
                    try:
                        if sec_role:
                            print(f"[on_voice_state_update] Check if bot can set channel for {sec_role.name} {voiceChannel}")
                            await textChannel.set_permissions(sec_role, read_messages=(not locked), send_messages=(not locked), read_message_history=(not locked), view_channel=True)
                            await voiceChannel.set_permissions(sec_role, speak=True, connect=(not locked), read_messages=(not locked), send_messages=(not locked), view_channel=True, stream=(not locked))
                    except Exception as ex:
                        print(ex)
                        traceback.print_exc()

                    await self.sendEmbed(textChannel, "Voice Text Channel", f'{member.mention}, This channel will be deleted when everyone leaves the associated voice chat.', delete_after=None, footer='')
                    initMessage = self.settings.initMessage
                    if initMessage:
                        # title, message, fields=None, delete_after=None, footer=None
                        await self.sendEmbed(textChannel, initMessage['title'], initMessage['message'], initMessage['fields'], delete_after=None, footer='')
            except discord.errors.NotFound as nf:
                print(nf)
            except Exception as ex:
                print(ex)
                traceback.print_exc()


    @voice.command()
    async def version(self, ctx):
        appName = utils.dict_get(self.settings.__dict__, "name", default_value = "Voice Create Bot")
        await self.sendEmbed(ctx.channel, "Version Information", f"Voice Create Bot Version: {self.settings.APP_VERSION}", delete_after=10)
        await ctx.message.delete()

    @voice.command()
    async def channels(self, ctx):
        self.db.open()
        guildID = ctx.author.guild.id
        try:
            if self.isAdmin(ctx):
                guild_channels = self.db.get_tracked_channels_for_guild(guildId=guildID)
                channelFields = list()
                for vc in guild_channels.voice_channels:
                    voice_channel = await self.get_or_fetch_channel(vc.voice_channel_id)
                    user = await self.get_or_fetch_user(vc.owner_id)
                    text_channel = None
                    tchanName = f"**[No Text Channel]**"
                    chanName = f"**[Unknown Channel: {str(vc.voice_channel_id)}]**"
                    userName = f"**[Unknown User: {str(vc.owner_id)}]**"
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
                    await self.sendEmbed(ctx.channel, "Tracked Channels", "Here are the currently tracked channels", fields=channelFields, delete_after=30)
                else:
                    await self.sendEmbed(ctx.channel, "Tracked Channels", "There are currently no tracked channels", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["track-text-channel", "ttc"])
    async def track_text_channel(self, ctx, channel: discord.TextChannel = None):
        guildID = ctx.author.guild.id
        self.db.open()
        try:
            if self.isAdmin(ctx):

                voiceChannel = None
                if ctx.author.voice:
                    voiceChannel = ctx.author.voice.channel

                if channel is None:
                    await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, You must specific a channel to track.", fields=None, delete_after=5)
                    await ctx.message.delete()
                    return

                if voiceChannel:
                    # check if this voice channel is tracked.
                    tracked = self.db.get_tracked_channels_for_guild(guildId=guildID)
                    tracked_voice_filter = [tv for tv in tracked.voice_channels if tv.voice_channel_id == voiceChannel.id]
                    tracked_text_filter = [tt for tt in tracked.text_channels if tt.voice_channel_id == voiceChannel.id]
                    if tracked_voice_filter:
                        tracked_voice = tracked_voice_filter[0]
                        if not tracked_text_filter:
                            # no tracked text channel
                            if channel.category_id == voiceChannel.category_id:
                                # text channel is in the same category as the voice channel
                                self.db.add_tracked_text_channel(guildId=guildID, ownerId=tracked_voice.owner_id, voiceChannelId=voiceChannel.id, textChannelId=channel.id)
                                await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, I am now tracking '{channel}' with '{voiceChannel}'.", fields=None, delete_after=5)
                            else:
                                # not in the same category
                                await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, {channel} is in a different category than '{voiceChannel}'. Tracking this channel is not supported.", fields=None, delete_after=5)
                        else:
                            tracked_text = tracked_text_filter[0]
                            # channel already has a textChannel associated with it.
                            # check if it exists
                            tc_lookup = await self.get_or_fetch_channel(tracked_text.text_channel_id)

                            if tc_lookup:
                                # channel exists. so we just exit
                                await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, The voice channel '{voiceChannel}' already has a channel associated with it", fields=None, delete_after=5)
                            else:
                                # old tracked channel missing
                                self.db.delete_tracked_text_channel(guildId=guildID, voiceChannelId=voiceChannel.id, textChannelId=tracked_text.text_channel_id)
                                if channel.category_id == voiceChannel.category_id:
                                    # text channel is in the same category as the voice channel
                                    self.db.add_tracked_text_channel(guildId=guildID, ownerId=tracked_voice.owner_id, voiceChannelId=voiceChannel.id, textChannelId=channel.id)
                                    await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, I am now tracking '{channel}' with '{voiceChannel}'.", fields=None, delete_after=5)
                                else:
                                    # not in the same category
                                    await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, {channel} is in a different category than '{voiceChannel}'. Tracking this channel is not supported.", fields=None, delete_after=5)

                    else:
                        # not tracked
                        await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, The voice channel you are in is not currently tracked, so I can't track '{channel}' with '{voiceChannel}'.", fields=None, delete_after=5)
                else:
                    await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}", f"You are not in a voice channel to link '{channel}' to.", fields=None, delete_after=5)
            else:
                await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, You do not have permission to add '{channel}' as a tracked channel", fields=None, delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def track(self, ctx):
        self.db.open()
        try:
            message_author_id = ctx.author.id
            guild_id = ctx.author.guild.id
            channel = ctx.author.voice.channel
            if not channel:
                await self.sendEmbed(ctx.channel, "Track Channel", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
            else:
                if self.isAdmin(ctx):
                    tracked_channels = self.db.get_tracked_channels_for_guild(guildId=guild_id)
                    filtered = [t for t in tracked_channels.voice_channels if t.voice_channel_id == channel.id]
                    if filtered:
                        await self.sendEmbed(ctx.channel, "Track Channel", f"{ctx.author.mention} This channel is already tracked.", delete_after=5)
                    else:
                        self.db.track_new_voice_channel(guildId=guild_id, ownerId=message_author_id, voiceChannelId=channel.id)
                        await self.sendEmbed(ctx.channel, "Track Channel", f"{ctx.author.mention} The channel '{channel.name}' is now tracked.\n\nUse the `.voice track-text-channel #channel-name` command to track the associated text channel.", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def owner(self, ctx, member: discord.Member):
        self.db.open()
        guildId = ctx.author.guild.id
        channel = None
        try:
            if self.isInVoiceChannel(ctx):
                channel = ctx.author.voice.channel
            if channel is None:
                await self.sendEmbed(ctx.channel, "Set Channel Owner", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
            else:
                owner_id = self.db.get_tracked_channel_owner(guildId=guildId, voiceChannelId=channel.id)
                if not owner_id:
                    await self.sendEmbed(ctx.channel, "Set Channel Owner", f"{ctx.author.mention} That channel is not managed by me. I can't help you own that channel.", delete_after=5)
                else:
                    if self.isAdmin(ctx) or ctx.author.id == owner_id:
                        self.db.update_tracked_channel_owner(guildId=guildId, voiceChannelId=channel.id, ownerId=owner_id, newOwnerId=member.id)
                        await self.sendEmbed(ctx.channel, "Channel Owner Updated", f"{ctx.author.mention}, {member.mention} is now the owner of the channel.", delete_after=5)
                    else:
                        await self.sendEmbed(ctx.channel, "Set Channel Owner", f"{ctx.author.mention}, You do not have permission to set the owner of the channel. If the owner left, try `claim`.", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def resync(self, ctx):
        try:
            self.db.open
            guild_id = ctx.guild.id
            category_id = ctx.author.voice.channel.category.id
            voice_channel = None
            voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                voice_channel_id = ctx.author.voice.channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return

            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if not self.isAdmin(ctx) and ctx.author.id != owner_id:
                await self.sendEmbed(ctx.channel, "Channel Sync", f'{ctx.author.mention} You do not own this channel, and do not have permissions to resync it.', delete_after=5)
                return

            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)
            if text_channel:
                await text_channel.edit(sync_permissions=True)
                await text_channel.set_permissions(ctx.author, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)

            await voice_channel.edit(sync_permissions=True)
            await voice_channel.set_permissions(ctx.author, speak=True, priority_speaker=True, connect=True, read_messages=True, send_messages=True, view_channel=True, stream=True)
            await self.sendEmbed(ctx.channel, "Channel Sync", f'{ctx.author.mention} The permissions of this channel have been resync\'d with the defaults. ♻', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def private(self, ctx):
        try:
            self.db.open()
            author_id = ctx.author.id
            category_id = ctx.author.voice.channel.category.id
            guild_id = ctx.guild.id
            voice_channel = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)

            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, "Channel Private", f'{ctx.author.mention} You do not own this channel, and do not have permissions to make it private.', delete_after=5)
                return
            owner_user = await self.get_or_fetch_user(owner_id)

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            await ctx.message.delete()
            await self.sendEmbed(ctx.channel, "Channel Private", f'{ctx.author.mention}, I am assigning permissions. This may take a moment.', delete_after=5)
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
            await voice_channel.set_permissions(owner_user, speak=True, view_channel=True, connect=True, use_voice_activation=False, stream=False )
            for r in permRoles:
                await voice_channel.set_permissions(r, speak=True, view_channel=True, connect=True, use_voice_activation=False, stream=False)
            # deny everyone else
            for r in denyRoles:
                await voice_channel.set_permissions(r, speak=False, view_channel=True, connect=False)
            await self.sendEmbed(ctx.channel, "Channel Private", f'{ctx.author.mention} This channel is locked for just the people in this channel.', delete_after=5)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
    @voice.command()
    async def hide(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        try:
            self.db.open()
            author_id = ctx.author.id
            guild_id = ctx.guild.id
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
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return

            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            owner = await self.get_or_fetch_user(owner_id)
            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, "Channel Mute", f'{ctx.author.mention} You do not own this channel, and do not have permissions to hide it.', delete_after=5)
                return

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            # everyone = discord.utils.get(ctx.guild.roles, name=default_role)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
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

            await self.sendEmbed(ctx.channel, "Channel Hide", f'{ctx.author.mention} Channel now hidden from users or specified role. 🙈', delete_after=5)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
    @voice.command()
    async def show(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        try:
            self.db.open()
            author_id = ctx.author.id
            guild_id = ctx.guild.id
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
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return

            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            owner = await self.get_or_fetch_user(owner_id)
            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, "Channel Mute", f'{ctx.author.mention} You do not own this channel, and do not have permissions to hide it.', delete_after=5)
                return

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            # everyone = discord.utils.get(ctx.guild.roles, name=default_role)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
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

            await self.sendEmbed(ctx.channel, "Channel Show", f'{ctx.author.mention} Channel now hidden from users or specified role. 👀', delete_after=5)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
    @voice.command()
    async def mute(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        try:
            self.db.open()
            author_id = ctx.author.id
            guild_id = ctx.guild.id
            category_id = None
            category = None
            voice_channel = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                category = voice_channel.category
                category_id = category.id
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            owner = await self.get_or_fetch_user(owner_id)

            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, "Channel Mute", f'{ctx.author.mention} You do not own this channel, and do not have permissions to mute it.', delete_after=5)
                return

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            # everyone = discord.utils.get(ctx.guild.roles, name=default_role)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
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

            await self.sendEmbed(ctx.channel, "Channel Mute", f'{ctx.author.mention} All users in the specified role are now muted 🔇', delete_after=5)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def unmute(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        try:
            self.db.open()
            author_id = ctx.author.id
            category_id = ctx.author.voice.channel.category.id
            guild_id = ctx.guild.id
            voice_channel = None
            if self.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            owner = await self.get_or_fetch_user(owner_id)
            if (not self.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self.sendEmbed(ctx.channel, "Channel Unmute", f'{ctx.author.mention} You do not own this channel, and do not have permissions to make it private.', delete_after=5)
                return

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            # everyone = discord.utils.get(ctx.guild.roles, name=default_role)
            everyone = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
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

            await self.sendEmbed(ctx.channel, "Channel Unmute", f'{ctx.author.mention} All users in the specified role are now unmuted 🗣', delete_after=5)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def setprefix(self, ctx, prefix="."):
        if self.isAdmin():
            if prefix:
                self.bot.command_prefix = prefix
                embed_fields = list()
                embed_fields.append({
                    "name": "Example",
                    "value": f"{prefix}voice name CoD:MW US"
                })
                await self.sendEmbed(ctx.channel, "Voice Channel Prefix", f'Command prefix is now "{prefix}".', delete_after=60)

    @voice.command()
    async def help(self, ctx, command=""):
        try:
            command_list = self.settings.commands
            if command and command.lower() in command_list:
                cmd = command_list[command.lower()]
                if not cmd['admin'] or (cmd['admin'] and self.isAdmin(ctx)):
                    fields = list()
                    fields.append({"name": "**Usage**", "value": f"`{cmd['usage']}`"})
                    fields.append({"name": "**Example**", "value": f"`{cmd['example']}`"})
                    fields.append({"name": "**Aliases**", "value": f"`{cmd['aliases']}`"})

                    await self.sendEmbed(ctx.channel, f"Command Help for **{command.lower()}**", cmd['help'], fields=fields)
            else:
                filtered_list = list()
                if self.isAdmin(ctx):
                    filtered_list = [i for i in command_list.keys()]
                else:
                    filtered_list = [i for i in command_list.keys() if command_list[i]['admin'] == False]

                chunked = utils.chunk_list(list(filtered_list), 10)
                pages = math.ceil(len(filtered_list) / 10)
                page = 1
                for chunk in chunked:
                    fields = list()
                    for k in chunk:
                        cmd = command_list[k.lower()]
                        if cmd['admin'] and self.isAdmin(ctx):
                            fields.append({"name": cmd['help'], "value": f"`{cmd['usage']}`"})
                            fields.append({"name": "More Help", "value": f"`.voice help {k.lower()}`"})
                            fields.append({"name": "Admin Command", "value": f"Can only be ran by a server admin"})
                        else:
                            fields.append({"name": cmd['help'], "value": f"`{cmd['usage']}`"})
                            fields.append({"name": "More Help", "value": f"`.voice help {k.lower()}`"})

                    await self.sendEmbed(ctx.channel, f"Voice Bot Command Help ({page}/{pages})", "List of Available Commands", fields=fields)
                    page += 1
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        await ctx.message.delete()

    @voice.command(pass_context=True)
    @has_permissions(administrator=True)
    async def init(self, ctx):
        if self.isAdmin(ctx):
            self.db.open()
            try:
                author = ctx.author
                author_id = ctx.author.id
                guild_id = ctx.guild.id
                def check_user(m):
                    return m.author.id == author_id
                def check_role(m):
                    if(check_user(m)):
                        # role = discord.utils.get(m.guild.roles,name=m.content)

                        role = self.get_by_name_or_id(m.guild.roles, m.content)
                        if role:
                            return True
                        return False

                selected_guild_role = await self.ask_default_role(ctx, "Voice Channel Initialization")
                if not selected_guild_role:
                    return

                selected_admin_role = await self.ask_admin_role(ctx, "Voice Channel Initialization")
                if not selected_admin_role:
                    return

                # ask bot prefix?
                prefix = "."
                await self.sendEmbed(ctx.channel, "Voice Channel Initialization", '**What would you like to set for the bot prefix?\n\nExample: `.`**', delete_after=60, footer="**You have 60 seconds to answer**")
                try:
                    prefixResp = await self.bot.wait_for('message', check=check_user, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, "Voice Channel Initialization", 'Took too long to answer!', delete_after=5)
                else:
                    prefix = prefixResp.content
                    await prefixResp.delete()


                self.db.insert_or_update_guild_settings(guildId=guild_id, prefix=prefix, defaultRole=selected_guild_role.id, adminRole=selected_admin_role.id)
                await self.sendEmbed(ctx.channel, "Voice Channel Initialization", 'You have successfully initialized the bot for this discord.', delete_after=5)
            except Exception as ex:
                print(ex)
                traceback.print_exc()
                await self.notify_of_error(ctx)
            finally:
                self.db.close()
                await ctx.message.delete()
        else:
            pass

    @voice.command(pass_context=True)
    @has_permissions(administrator=True)
    async def setup(self, ctx):
        self.db.open()
        guild_id = ctx.guild.id
        try:
            print(f"[setup] User id triggering setup: {ctx.author.id}")
            author_id = ctx.author.id
            # If the person is the OWNER or an ADMIN
            if self.isAdmin(ctx):
                def check(m):
                    return m.author.id == author_id
                def check_yes_no(m):
                    if(check(m)):
                        msg = m.content
                        result = utils.str2bool(msg)
                        return result == True or result == False
                def check_limit(m):
                    if check(m):
                        if m.content.isnumeric():
                            val = int(m.content)
                            return val >= 0 and val <= 100
                        else:
                            return False
                def check_role(m):
                    if(check(m)):
                        guild_roles = m.guild.roles
                        if m.content == "DEFAULT":
                            m_guild_settings = self.db.get_guild_settings(m.guild.id)
                            if m_guild_settings:
                                return self.get_by_name_or_id(guild_roles, m_guild_settings.default_role)
                            # return discord.utils.get(guild_roles, name=self.settings.default_role or "everyone")
                            return self.get_by_name_or_id(guild_roles, self.settings.default_role or "everyone")
                        # is valid role?
                        # role = discord.utils.get(m.guild.roles,name=m.content)
                        role = self.get_by_name_or_id(guild_roles, m.content)
                        print(f"[setup] ROLE: {role}")
                        if role:
                            return True
                        return False
                def check_bitrate(m):
                    if check(m):
                        if m.content.isnumeric():
                            bitrate_min = 8
                            bitrate_limit = int(round(m.guild.bitrate_limit / 1000))
                            set_br = int(m.content)
                            return set_br == 0 or (set_br >= bitrate_min and set_br <= bitrate_limit)
                        return False
                guild_settings = self.db.get_guild_settings(guildId=guild_id)
                if not guild_settings:
                    await self.sendEmbed(ctx.channel, "Voice Channel Setup", 'Voice Create bot not configured for this discord.\n\n\n**Please run `init` command.**', delete_after=10)
                    return
                # Ask them for the category name
                category = await self.ask_category(ctx)
                if category is None:
                    return
                useStage = False
                is_community = ctx.guild.features.count("COMMUNITY") > 0
                if is_community:
                    await self.sendEmbed(ctx.channel, "Voice Channel Setup", '**Would you like to use a Stage Channel?\n\nReply: YES or NO.**', delete_after=60, footer="**You have 60 seconds to answer**")
                    try:
                        useStageResp = await self.bot.wait_for('message', check=check_yes_no, timeout=60)
                    except asyncio.TimeoutError:
                        await self.sendEmbed(ctx.channel, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
                        return
                    else:
                        useStage = utils.str2bool(useStageResp.content)
                        await useStageResp.delete()

                await self.sendEmbed(ctx.channel, "Voice Channel Setup", '**Enter the name of the voice channel: (e.g Join To Create)**', delete_after=60, footer="**You have 60 seconds to answer**")
                try:
                    channelName = await self.bot.wait_for('message', check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
                else:
                    try:
                        channel = await ctx.guild.create_voice_channel(channelName.content, category=category)
                        await channelName.delete()

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

                            # ASK SET DEFAULT CHANNEL LIMIT
                            defaultLimit = 0
                            await self.sendEmbed(ctx.channel, "Voice Channel Setup", '**Set the default channel limit.\n\nReply: 0 - 100.**', delete_after=60, footer="**You have 60 seconds to answer**")
                            try:
                                defaultLimitResp = await self.bot.wait_for('message', check=check_limit, timeout=60)
                            except asyncio.TimeoutError:
                                await self.sendEmbed(ctx.channel, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
                                return
                            else:
                                defaultLimit = int(defaultLimitResp.content)
                                await defaultLimitResp.delete()

                            # ASK SET DEFAULT CHANNEL LOCKED
                            defaultLocked = False
                            await self.sendEmbed(ctx.channel, "Voice Channel Setup", '**Would you like the channels LOCKED 🔒 by default?\n\nReply: YES or NO.**', delete_after=60, footer="**You have 60 seconds to answer**")
                            try:
                                defaultLockedResponse = await self.bot.wait_for('message', check=check_yes_no, timeout=60)
                            except asyncio.TimeoutError:
                                await self.sendEmbed(ctx.channel, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
                                return
                            else:
                                defaultLocked = utils.str2bool(defaultLockedResponse.content)
                                await defaultLockedResponse.delete()

                            # ASK SET DEFAULT BITRATE
                            defaultBitrate = 64

                            bitrate_min = 8
                            bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))
                            await self.sendEmbed(ctx.channel, "Voice Channel Setup", f'**Set the default channel bitrate.\n\nReply: {str(bitrate_min)} - {str(bitrate_limit)}\n\n\nUse 0 for default bitrate.**', delete_after=60, footer="**You have 60 seconds to answer**")
                            try:
                                bitrateResp = await self.bot.wait_for('message', check=check_bitrate, timeout=60)
                            except asyncio.TimeoutError:
                                await self.sendEmbed(ctx.channel, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
                                return
                            else:
                                defaultBitrate = int(bitrateResp.content)
                                if defaultBitrate == 0:
                                    defaultBitrate = self.settings.BITRATE_DEFAULT
                                await bitrateResp.delete()


                            selected_guild_role = await self.ask_default_role(ctx, "Voice Channel Setup")
                            if not selected_guild_role:
                                # selected_guild_role = discord.utils.get(ctx.guild.roles, name=guild_settings.default_role or self.settings.default_role or "@everyone").name
                                selected_guild_role = self.get_by_name_or_id(ctx.guild.roles, guild_settings.default_role or self.settings.default_role or "everyone")

                            self.db.set_guild_category_settings(guildId=guild_id, categoryId=category.id, channelLimit=defaultLimit, channelLocked=defaultLocked, bitrate=defaultBitrate, defaultRole=selected_guild_role.id)
                        else:
                            print(f"[setup] GUILD CATEGORY SETTINGS FOUND")
                            print(json.dumps(guild_category_settings.__dict__))
                        await ctx.channel.send("**You are all setup and ready to go!**", delete_after=5)
                    except Exception as e:
                        traceback.print_exc()
                        await self.sendEmbed(ctx.channel, "Voice Channel Setup", "You didn't enter the names properly.\nUse `.voice setup` again!", delete_after=5)
            else:
                await self.sendEmbed(ctx.channel, "Voice Channel Setup", f"{ctx.author.mention} only the owner or admins of the server can setup the bot!", delete_after=10)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @setup.error
    async def info_error(self, ctx, error):
        print(error)
        traceback.print_exc()

    @voice.command(aliases=['get-default-role', 'gdr'])
    async def get_default_role(self, ctx):
            try:
                if self.isAdmin(ctx):
                    if self.isInVoiceChannel(ctx):
                        guild_id = ctx.guild.id
                        voice_channel = ctx.author.voice.channel
                        # category_id = ctx.author.voice.channel.category.id
                        self.db.open()
                        user_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel.id)
                        default_role = self.db.get_default_role(guildId=guild_id, categoryId=voice_channel.category.id, userId=user_id)
                        if default_role:
                            role = self.get_by_name_or_id(ctx.guild.roles, default_role)
                            await self.sendEmbed(ctx.channel, "Channel Settings", f"The default role applied to the channel or category you are in is: `{role}`", fields=None, delete_after=30)
                        else:
                            await self.sendEmbed(ctx.channel, "Channel Settings", f"I was unable to locate default role information based on the channel and category you are in.", fields=None, delete_after=5)
                    else:
                        await self.sendEmbed(ctx.channel, "Channel Settings", f"You must be in a voice channel to use this command", fields=None, delete_after=5)
                else:
                    print(f"[get_default_role] {ctx.author.mention} attempted to call get_default_role")
            except Exception as ex:
                print(ex)
                traceback.print_exc()
                await self.notify_of_error(ctx)
            finally:
                await ctx.message.delete()
                self.db.close()

    @voice.command(aliases=['set-default-role', 'sdr'])
    async def set_default_role(self, ctx, default_role: typing.Union[discord.Role, str]):
        if self.isAdmin(ctx):

            temp_default_role = default_role
            if not isinstance(temp_default_role, discord.Role):
                temp_default_role = discord.utils.get(ctx.guild.roles, name=temp_default_role)
            guild_id = ctx.guild.id
            self.db.open()
            try:
                category = await self.set_role_ask_category(ctx)
                if category:
                    category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category.id)
                    if category_settings:
                        self.db.set_default_role_for_category(guildId=guild_id, categoryId=category.id, defaultRole=temp_default_role.id)
                    else:
                        await self.sendEmbed(ctx.channel, "Channel Category Settings", f"Existing settings not found. Use `.voice settings` to configure.", fields=None, delete_after=5)
                else:
                    print(f"[set_default_role] unable to locate the expected category")
            except Exception as ex:
                print(ex)
                traceback.print_exc()
            finally:
                self.db.close()
                await ctx.message.delete()

    @voice.command()
    async def settings(self, ctx, category: str = None, locked: str = "False", limit: int = 0, bitrate: int = 64, default_role: typing.Union[discord.Role, str] = None):
        if self.isAdmin(ctx):
            guild_id = ctx.guild.id
            self.db.open()
            try:
                if category is None:
                    category = await self.set_role_ask_category(ctx)
                found_category = next((x for x in ctx.guild.categories if x.name == category), None)
                if found_category:
                    bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))
                    bitrate_min = 8
                    br = int(bitrate)

                    if br > bitrate_limit:
                        br = bitrate_limit
                    elif br < bitrate_min:
                        br = bitrate_min

                    temp_default_role = default_role
                    if not isinstance(temp_default_role, discord.Role):
                        temp_default_role = discord.utils.get(ctx.guild.roles, name=temp_default_role)
                    else:
                        temp_default_role = default_role.name
                    new_default_role = temp_default_role
                    if not new_default_role:
                        new_default_role = discord.utils.get(ctx.guild.roles, self.settings.default_role)

                    self.db.set_guild_category_settings(guildId=guild_id, categoryId=found_category.id, channelLimit=int(limit), channelLocked=utils.str2bool(locked), bitrate=int(br), defaultRole=new_default_role.id)
                    embed_fields = list()
                    embed_fields.append({
                        "name": "Locked",
                        "value": str(locked)
                    })
                    embed_fields.append({
                        "name": "Limit",
                        "value": str(limit)
                    })
                    embed_fields.append({
                        "name": "Bitrate",
                        "value": f"{str(bitrate)}kbps"
                    })
                    embed_fields.append({
                        "name": "Default Role",
                        "value": f"{new_default_role.name}"
                    })

                    await self.sendEmbed(ctx.channel, "Channel Category Settings", f"Category '{category}' settings have been set.", fields=embed_fields, delete_after=5)

                else:
                    print(f"[settings] No Category found for '{category}'")
            except Exception as ex:
                print(ex)
                traceback.print_exc()
                await self.notify_of_error(ctx)
            finally:
                self.db.close()
        else:
            await self.sendEmbed(ctx.channel, "Channel Category Settings", f"{ctx.author.mention} only the owner or admins of the server can setup the bot!", delete_after=5)
        await ctx.message.delete()

    @voice.command()
    async def cleandb(self,ctx):
        try:
            if self.isAdmin(ctx):
                self.db.open()
                guild_id = ctx.guild.id
                self.db.clean_guild_user_settings(guildId=guild_id)
                await self.sendEmbed(ctx.channel, "Clean Database", "All User Settings have been purged from database.", delete_after=5)
            else:
                await self.sendEmbed(ctx.channel, "Permission Denied", f"{ctx.author.mention}, you do not have permission to run this command.", delete_after=5)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def reset(self,ctx, user: discord.Member = None):
        try:
            author = ctx.author
            if user and self.isAdmin(ctx):
                author = user
            guild_id = ctx.guild.id
            self.db.clean_user_settings(guildId=guild_id, userId=author.id)
            await self.sendEmbed(ctx.channel, "Reset User Settings", f"{author.mention}, I have reset your settings.", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def lock(self, ctx, role: discord.Role = None):
        try:
            owner_id = ctx.author.id
            owner = ctx.author
            guild_id = ctx.guild.id
            category_id = ctx.author.voice.channel.category.id
            current_voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                current_voice_channel = ctx.author.voice.channel
                current_voice_channel_id = current_voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return

            if self.isAdmin(ctx):
                owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=current_voice_channel_id)
                owner = await self.get_or_fetch_user(owner_id)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)

            validRole = len([ x for x in ctx.guild.roles if x.name == default_role or x.id == default_role ]) == 1
            if not validRole:
                default_role = ctx.guild.default_role.id
            print(f"[lock] default role: {default_role}")
            owned_channel_ids = self.db.get_tracked_voice_channel_id_by_owner(guildId=guild_id,ownerId=owner_id)
            is_owner = len([ c for c in owned_channel_ids if int(c) == current_voice_channel_id ]) >= 1
            if not is_owner and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Channel Lock", f'{ctx.author.mention} You do not own this channel, and do not have permissions to lock it.', delete_after=5)
            else:
                # everyone = discord.utils.get(ctx.guild.roles, name=default_role)
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

                await self.sendEmbed(ctx.channel, "Channel Lock", f'{ctx.author.mention} Voice chat locked! 🔒', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def unlock(self, ctx, role: discord.Role = None):
        try:
            owner_id = ctx.author.id
            owner = ctx.author
            guild_id = ctx.guild.id
            category_id = ctx.author.voice.channel.category.id
            current_voice_channel_id = None
            if self.isInVoiceChannel(ctx):
                current_voice_channel = ctx.author.voice.channel
                current_voice_channel_id = current_voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return

            if self.isAdmin(ctx):
                owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=current_voice_channel_id)
                owner = await self.get_or_fetch_user(owner_id)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id) or self.settings.default_role

            validRole = len([ x for x in ctx.guild.roles if x.name == default_role or x.id == default_role ]) == 1
            if not validRole:
                default_role = ctx.guild.default_role.id
            print(f"[unlock] default role: {default_role}")
            owned_channel_ids = self.db.get_tracked_voice_channel_id_by_owner(guildId=guild_id,ownerId=owner_id)
            is_owner = len([ c for c in owned_channel_ids if int(c) == current_voice_channel_id ]) >= 1
            if not is_owner and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Channel Lock", f'{ctx.author.mention} You do not own this channel, and do not have permissions to lock it.', delete_after=5)
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

                await self.sendEmbed(ctx.channel, "Channel Lock", f'{ctx.author.mention} Voice chat unlocked! 🔓', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["allow"])
    async def permit(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        self.db.open()
        guild_id = ctx.guild.id
        voice_channel_id = None
        text_channel = None
        if self.isInVoiceChannel(ctx):
            voice_channel = ctx.author.voice.channel
            voice_channel_id = voice_channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if not self.isAdmin(ctx) and ctx.author.id != owner_id:
                await self.sendEmbed(ctx.channel, "Grant User Access", f'{ctx.author.mention} You do not own this channel, and do not have permissions to allow access.', delete_after=5)
                return
            text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            if text_channel_id:
                text_channel = await self.get_or_fetch_channel(text_channel_id)

            if text_channel:
                if userOrRole:
                    await text_channel.set_permissions(userOrRole, read_messages=True, send_messages=True, view_channel=True, read_message_history=True, )
            if userOrRole:
                await voice_channel.set_permissions(userOrRole, connect=True, view_channel=True, speak=True, stream=True)
                await self.sendEmbed(ctx.channel, "Grant User Access", f'{ctx.author.mention} You have permitted {userOrRole.name} to have access to the channel. ✅', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        self.db.open()
        guild_id = ctx.guild.id
        voice_channel_id = None
        text_channel = None
        voice_channel = None
        if self.isInVoiceChannel(ctx):
            voice_channel = ctx.author.voice.channel
            voice_channel_id = voice_channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if not self.isAdmin(ctx) and ctx.author.id != owner_id:
                await self.sendEmbed(ctx.channel, "Grant User Access", f'{ctx.author.mention} You do not own this channel, and do not have permissions to allow access.', delete_after=5)
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
            await self.sendEmbed(ctx.channel, "Reject User Access", f'{ctx.author.mention} You have rejected {userOrRole} from accessing the channel. ❌', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def limit(self, ctx, limit):
        try:
            self.db.open()
            guild_id = ctx.guild.id
            author = ctx.author
            owner = ctx.author
            owner_id = owner.id
            category_id = ctx.author.voice.channel.category.id

            channel_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = owner.voice.channel
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if self.isAdmin(ctx) or owner_id == author.id:
                owner = await self.get_or_fetch_user(owner_id)
            else:
                await self.sendEmbed(ctx.channel, "Permission Denied", f'{author.mention} You are not an admin, nor are you the owner of this channel.', delete_after=5)
                return

            await voice_channel.edit(user_limit=limit)
            await self.sendEmbed(ctx.channel, "Set Channel Limit", f'{ctx.author.mention} You have set the channel limit to be ' + '{}!'.format(limit), delete_after=5)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
            user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
            category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
            if user_settings:
                self.db.update_user_limit(guildId=guild_id, userId=owner_id, channelLimit=limit)
            else:
                self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=voice_channel.name, channelLimit=limit, bitrate=category_settings.bitrate, defaultRole=temp_default_role.id, autoGame=False)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def bitrate(self, ctx, bitrate: int = 64):
        try:
            self.db.open()
            guild_id = ctx.guild.id
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
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if self.isAdmin(ctx) or owner_id == author.id:
                owner = await self.get_or_fetch_user(owner_id)
            else:
                await self.sendEmbed(ctx.channel, "Permission Denied", f'{author.mention} You are not an admin, nor are you the owner of this channel.', delete_after=5)
                return
            br_set = int(bitrate)

            if br_set > bitrate_limit:
                await self.sendEmbed(ctx.channel, "Updated Channel Bitrate", f"{ctx.author.mention}, your bitrate is above the bitrate limit of {bitrate_limit}kbps. I will apply the the limit instead.", delete_after=5)
                br_set = bitrate_limit
            elif br_set < bitrate_min:
                await self.sendEmbed(ctx.channel, "Updated Channel Bitrate", f"{ctx.author.mention}, your bitrate is below the bitrate minimum of {bitrate_min}kbps. I will apply the the minimum instead.", delete_after=5)
                br_set = bitrate_min

            br = br_set * 1000
            await voice_channel.edit(bitrate=br)
            await self.sendEmbed(ctx.channel, "Updated Channel Bitrate", f'{ctx.author.mention}, you have set the channel bitrate to be ' + '{}kbps!'.format(br_set), delete_after=5)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
            user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
            category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
            if user_settings:
                self.db.update_user_bitrate(guildId=guild_id, userId=owner_id, bitrate=br_set)
            else:
                self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=voice_channel.name, channelLimit=category_settings.channel_limit, bitrate=br_set, defaultRole=temp_default_role.id, autoGame=False)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command(aliases=["enable-auto-game", "eag"])
    async def auto_game(self, ctx, enabled: str):
        try:
            guild_id = ctx.guild.id
            author = ctx.author
            owner_id = None
            if self.isInVoiceChannel(ctx):
                voice_channel = author.voice.channel
                channel_category_id = voice_channel.category.id
                voice_channel_id = voice_channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id != author.id:
                await self.sendEmbed(ctx.channel, "Permission Denied", f'{author.mention} You are not an admin, nor are you the owner of this channel.', delete_after=5)
                return

            enable_auto = utils.str2bool(enabled)
            user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
            default_role = self.db.get_default_role(guildId=guild_id, categoryId=channel_category_id, userId=owner_id)
            temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
            print(f"[auto_game] default_role: {str(default_role or self.settings.default_role)}")
            if temp_default_role is None:
                temp_default_role = self.get_by_name_or_id(ctx.guild.roles, "@everyone" )
            if user_settings:
                self.db.set_user_settings_auto_game(guildId=guild_id, userId=owner_id, autoGame=enable_auto)
            else:
                self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=voice_channel.name, channelLimit=0, bitrate=self.settings.BITRATE_DEFAULT, defaultRole=temp_default_role.id, autoGame=enable_auto)
            state = "disabled"
            if enable_auto:
                state = "enabled"
            await self.sendEmbed(ctx.channel, "Enable Auto Game", f'{author.mention} You have {state} the changing of your channel name based on your game.', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()
    @voice.command()
    async def game(self, ctx):
        def check_user(m):
            return m.author.id == ctx.author.id
        def check_numeric(m):
            if check_user(m):
                return m.content.isnumeric()
        try:
            author = ctx.author
            author_id = author.id
            guild_id = ctx.guild.id
            channel_id = None
            selected_title = None
            if self.isInVoiceChannel(ctx):
                channel_id = ctx.author.voice.channel.id
            else:
                await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
                return
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=channel_id)
            if owner_id != author_id and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Set Channel Name", f'{ctx.author.mention} You do not own this channel, and do not have permissions to set the channel limit.', delete_after=5)
                return
            owner = await self.get_or_fetch_member(ctx.guild, owner_id)
            fields = list()
            titles = list()
            index = 0
            if owner:
                if owner.activities:
                    game_activity = [a for a in owner.activities if a.type == discord.ActivityType.playing]
                    stream_activity = [a for a in owner.activities if a.type == discord.ActivityType.streaming]
                    watch_activity = [a for a in owner.activities if a.type == discord.ActivityType.watching]

                    if game_activity:
                        for a in game_activity:
                            titles.append(a.name)
                            print(f"[game] game.name: {a.name}")
                        # name = game_activity[0].name
                    elif stream_activity:
                        for a in stream_activity:
                            # name = stream_activity[0].name
                            print(f"[game] stream.game: {a.game}")
                            print(f"[game] stream.name: {a.name}")
                            titles.append(a.game)
                            titles.append(a.name)
                        # name = stream_activity[0].game
                    elif watch_activity:
                        for a in watch_activity:
                            # name = watch_activity[0].name
                            print(f"[game] watch.name: {a.name}")
                            titles.append(a.name)
                    else:
                        print(f"Activities: {str(len(owner.activities))}")
                        for a in owner.activities:
                            titles.append(a.name)
                            print(f"[game] activity.name: {a.name}")

                    if len(titles) > 1:
                        index = 0
                        for t in titles:
                            fields.append(EmbedField(f"{str(index+1)}: {t}", f"Enter {index+1} to choose this title").__dict__)
                            index += 1
                        await self.sendEmbed(ctx.channel, "Multiple Options", f'{ctx.author.mention}, please choose from the game/stream/activity titles.', fields=fields,delete_after=60, footer="**You have 60 seconds to answer**")
                        try:
                            titleResp = await self.bot.wait_for('message', check=check_numeric, timeout=60.0)
                        except asyncio.TimeoutError:
                            await self.sendEmbed(ctx.channel, title, 'Took too long to answer!', delete_after=5)
                        else:
                            if titleResp.content.isnumeric():
                                idx = int(titleResp.content) - 1
                                if idx >= 0 and idx < len(titles):
                                    selected_title = titles[idx]
                                    if selected_title:
                                        await self.sendEmbed(ctx.channel, "Multiple Options", f"You selected: '{selected_title}'", delete_after=5)
                            await titleResp.delete()
                    elif len(titles) == 1:
                        selected_title = titles[0]

                else:
                    print(f"[game] owner.activity is None")

                if selected_title:
                    await self._name(ctx, name=selected_title, saveSettings=False)
                    # message deleted by the name call.
                else:
                    await self.sendEmbed(ctx.channel, "Unable to get Game", f'{ctx.author.mention} I was unable to determine the game title.', delete_after=5)
                    await ctx.message.delete()
            else:
                print(f"[game] Unable to locate the owner for 'game' call.")
                await ctx.message.delete()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)

    @voice.command()
    async def name(self, ctx, *, name: str = None):
        await self._name(ctx, name=name, saveSettings=True)

    async def _name(self, ctx, name: str = None, saveSettings: bool = True):
        voice_channel_id = None
        voice_channel = None
        if self.isInVoiceChannel(ctx):
            voice_channel_id = ctx.author.voice.channel.id
            voice_channel = ctx.author.voice.channel
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        if not name or name == "":
            name = utils.get_random_name()
        self.db.open()
        author_id = ctx.author.id
        guild_id = ctx.guild.id
        category_id = ctx.author.voice.channel.category.id
        try:
            owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id != author_id and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Set Channel Name", f'{ctx.author.mention} You do not own this channel, and do not have permissions to set the channel limit.', delete_after=5)
                return
            category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)

            default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
            is_tracked_channel = len([c for c in self.db.get_tracked_voice_channel_id_by_owner(guildId=guild_id, ownerId=owner_id) if c == voice_channel_id]) >= 1
            if not is_tracked_channel:
                await self.sendEmbed(ctx.channel, "Set Channel Name", f'{ctx.author.mention}, this channel is not tracked by me.', delete_after=5)
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
            await self.sendEmbed(ctx.channel, "Updated Channel Name", f'{ctx.author.mention}, you have changed the channel name to {name}.', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()


    @voice.command(aliases=["rename"])
    async def force_name(self, ctx, *, name: str = None):
        self.db.open()
        guild_id = ctx.guild.id
        channel_id = ctx.author.voice.channel.id
        channel = ctx.author.voice.channel
        try:
            if not self.isInVoiceChannel(ctx):
                await self.sendEmbed(ctx.channel, "Updated Channel Name", f'You are not currently in a voice channel!', delete_after=5)
                return
            if self.isAdmin(ctx):
                if not name or name == "":
                    name = utils.get_random_name()
                category_id = ctx.author.voice.channel.category.id
                guild_category_settings = self.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
                owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=channel_id)
                if not owner_id:
                    await self.sendEmbed(ctx.channel, "Updated Channel Name", f"I cannot determine who is the owner of this voice channel. Is it tracked?", delete_after=5)
                    return
                user_settings = self.db.get_user_settings(guildId=guild_id, userId=owner_id)
                default_role = self.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
                temp_default_role = self.get_by_name_or_id(ctx.guild.roles, default_role or self.settings.default_role)
                # text channel rename is automatically handled by the change event on the voice channel.

                if channel:
                    print(f"[rename] edit the channel to: {channel.name} -> {name}")
                    await channel.edit(name=name)
                    await self.sendEmbed(ctx.channel, "Updated Channel Name", f'{ctx.author.mention}, you have changed the channel name to {name}.', delete_after=5)

                if user_settings:
                    self.db.update_user_channel_name(guildId=guild_id, userId=owner_id, channelName=name)
                else:
                    self.db.insert_user_settings(guildId=guild_id, userId=owner_id, channelName=name, channelLimit=guild_category_settings.channel_limit, bitrate=guild_category_settings.bitrate, defaultRole=temp_default_role.id, autoGame=False)
            else:
                print(f"[rename] {ctx.author} tried to run command 'rename'")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def whoowns(self, ctx):
        try:
            self.db.open()
            guildID = ctx.guild.id
            channel = ctx.author.voice.channel
            if channel == None:
                await self.sendEmbed(ctx.channel, "Who Owns Channel", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
            else:
                owner_id = self.db.get_channel_owner_id(guildId=guildID, channelId=channel.id)
                if owner_id:
                    owner = ctx.guild.get_member(int(owner_id))
                    if not owner:
                        owner = await ctx.guild.fetch_member(int(owner_id))
                    if owner:
                        await self.sendEmbed(ctx.channel, "Who Owns Channel", f"{ctx.author.mention} The channel '{channel.name}' is owned by {owner.mention}!", delete_after=30)
                    else:
                        await self.sendEmbed(ctx.channel, "Who Owns Channel", f"{ctx.author.mention} The channel '{channel.name}' is owned by an unknown user (UserId: {owner_id})!", delete_after=30)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def give(self, ctx, newOwner: discord.Member):
        """Give ownership of the channel to another user in the channel"""
        self.db.open()
        guildID = ctx.guild.id
        if not self.isInVoiceChannel(ctx):
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            channel = ctx.author.voice.channel
            channel_id = ctx.author.voice.channel.id
            new_owner_id = newOwner.id
            # update_tracked_channel_owner
            owner_id = self.db.get_channel_owner_id(guildId=guildID, channelId=channel_id)
            if new_owner_id == owner_id:
                # Can't grant to self
                await self.sendEmbed(ctx.channel, "Change Channel Owner", f"{ctx.author.mention} You already own this channel.", delete_after=5)
            else:
                self.db.update_tracked_channel_owner(guildId=guildID, voiceChannelId=channel_id, ownerId=owner_id, newOwnerId=new_owner_id)
                await self.sendEmbed(ctx.channel, "Updated Channel Owner", f"{ctx.author.mention}, {newOwner.mention} is now the owner of '{channel.name}'!", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    async def claim(self, ctx):
        found_as_owner = False
        self.db.open()
        guildID = ctx.guild.id
        if not self.isInVoiceChannel(ctx):
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            channel = ctx.author.voice.channel
            aid = ctx.author.id

            owner_id = self.db.get_channel_owner_id(guildId=guildID, channelId=channel.id)
            if not owner_id and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Updated Channel Owner", f"{ctx.author.mention} You can't own that channel!", delete_after=5)
            else:
                for data in channel.members:
                    if data.id == owner_id:
                        owner = ctx.guild.get_member(owner_id)
                        await self.sendEmbed(ctx.channel, "Updated Channel Owner", f"{ctx.author.mention} This channel is already owned by {owner.mention}!", delete_after=5)
                        found_as_owner = True
                        break
                if not found_as_owner:
                    self.db.update_tracked_channel_owner(guildId=guildID, voiceChannelId=channel.id, ownerId=owner_id, newOwnerId=aid)
                    await self.sendEmbed(ctx.channel, "Updated Channel Owner", f"{ctx.author.mention} You are now the owner of the channel!", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            await self.notify_of_error(ctx)
        finally:
            self.db.close()
            await ctx.message.delete()

    @voice.command()
    # @commands.has_role("Admin")
    async def delete(self, ctx):
        if self.isAdmin(ctx):
            guildID = ctx.guild.id
            try:
                self.db.open()
                tracked_voice_channels_ids = [item for clist in self.db.get_tracked_voice_channel_ids(guildId=guildID) for item in clist]
                tracked_voice_channels = [chan for chan in ctx.guild.channels if chan.id in tracked_voice_channels_ids]
                embed = discord.Embed(title=f"Delete Voice Channel", description="Choose Which Voice Channel To Delete.", color=0x7289da)
                embed.set_author(name=f"{self.settings.name} v{self.settings.APP_VERSION}", url=self.settings.url,
                                icon_url=self.settings.icon)
                channel_array = []
                index = 0
                for c in tracked_voice_channels:
                    channel_array.append(c.id)
                    embed.add_field(name=f'{index+1}: {c.category.name}/{c.name}', value=f"Enter: {index+1} to delete.", inline='false')
                    index += 1
                embed.set_footer(text=f'--- You have 60 seconds to respond. ---')
                await ctx.channel.send(embed=embed, delete_after=65)
                selected_index = -1
                try:
                    def check_index(m):
                        idx = int(m.content)
                        result = m.content.isnumeric() and idx > 0 and idx <= len(channel_array)
                        return result
                    result_message = await self.bot.wait_for('message', check=check_index, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, "Timeout", f'You took too long to answer.', delete_after=5)
                else:
                    selected_index = int(result_message.content)
                    await result_message.delete()
                    if selected_index >= 0:
                        chan = await self.get_or_fetch_channel(channel_array[selected_index - 1])

                        if chan:
                            print(f"[delete] Attempting to remove users in {chan}")
                            for mem in chan.members:
                                mem.disconnect()
                            await self.sendEmbed(ctx.channel, "Channel Deleted", f'The channel {chan.name} has been deleted.', delete_after=5)
            except Exception as ex:
                print(ex)
                traceback.print_exc()
                await self.notify_of_error(ctx)
            finally:
                self.db.close()
                await ctx.message.delete()
        else:
            print(f"[delete] {ctx.author} tried to run command 'delete'")

    async def set_role_ask_category(self, ctx):
        try:
            found_category = None
            if self.isAdmin(ctx):
                def check(m):
                    same = m.author.id == ctx.author.id
                    return same
                def check_yes_no(m):
                    msg = m.content
                    return utils.str2bool(msg)
                await self.sendEmbed(ctx.channel, "Set Default Role", f"**Enter the name of the category you wish to set the default role for**", delete_after=60, footer="**You have 60 seconds to answer**")
                try:
                    category = await self.bot.wait_for('message', check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await ctx.channel.send('Took too long to answer!', delete_after=5)
                else:
                    found_category = next((x for x in ctx.guild.categories if x.name.lower() == category.content.lower()), None)
                    await category.delete()
                    if found_category:
                        # found existing with that name.
                        # do you want to create a new one?
                        yes_or_no = False
                        await self.sendEmbed(ctx.channel, "Set Default Role", f"**Is this the correct category? '{str(found_category.name.upper())}'.\n\nReply: YES or NO.**", delete_after=60, footer="**You have 60 seconds to answer**")
                        try:
                            yes_or_no = await self.bot.wait_for('message', check=check_yes_no, timeout=60.0)
                        except asyncio.TimeoutError:
                            await self.sendEmbed(ctx.channel, "Set Default Role", 'Took too long to answer!', delete_after=5)
                        else:
                            if yes_or_no:
                                await yes_or_no.delete()
                                return found_category
                            else:
                                return None
                    else:
                        return None
            else:
                return None
        except Exception as e:
            print(e)
            traceback.print_exc(e)
        finally:
            await ctx.message.delete()
    async def ask_admin_role(self, ctx, title: str = "Voice Channel Initialization"):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        # ask admin role
        index = 0
        idx = -1
        fields = list()
        admin_roles = [r.name for r in ctx.guild.roles if r.permissions.administrator]
        # chunked = utils.chunk_list(admin_roles, 20)
        # total_pages = math.ceil(len(admin_roles) / 20)

        for r in admin_roles:
            fields.append(EmbedField(f"{str(index+1)}: {r}", f"Enter {str(index+1)} to choose this role").__dict__)
            index += 1
        await self.sendEmbed(ctx.channel, title, '**What is your server admin role?\n\nChoose from the list:**', fields=fields, delete_after=60, footer="**You have 60 seconds to answer**")
        try:
            roleResp = await self.bot.wait_for('message', check=check_user, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, 'Took too long to answer!', delete_after=5)
        else:
            admin_role = None
            if roleResp.content.isnumeric():
                idx = int(roleResp.content) - 1
                if idx >= 0 and idx < len(admin_roles):
                    selected_admin_role_name = admin_roles[idx]
                    # admin_role = discord.utils.get(ctx.guild.roles, name=selected_admin_role_name)
                    admin_role = self.get_by_name_or_id(ctx.guild.roles, selected_admin_role_name)
                    if admin_role:
                        await self.sendEmbed(ctx.channel, title, f"You chose the role: '{admin_role.name}'", delete_after=5)

            await roleResp.delete()
        if not admin_role:
            await self.sendEmbed(ctx.channel, title, 'I was unable to verify that role as a valid discord administrator role.', delete_after=5)
            return None
        return admin_role
    async def ask_default_role(self, ctx, title: str = "Voice Channel Setup"):
        # ASK DEFAULT ROLE
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same

        index = 0
        idx = -1
        fields = list()
        guild_roles = [r.name for r in ctx.guild.roles]
        await self.sendEmbed(ctx.channel, title, '**What should the default role be?**\n\nThis is the role that will be the minimum permission for the the channel.', delete_after=60, footer="**You have 60 seconds to answer**")
        selected_guild_role = None
        chunked = utils.chunk_list(list(guild_roles), 20)
        total_pages = math.ceil(len(guild_roles) / 20)
        page = 1
        selected_guild_role = None
        for chunk in chunked:
            fields = list()
            for r in chunk:
                fields.append(EmbedField(f"{str(index+1)}: {r}", f"Enter {str(index+1)} to choose this role").__dict__)
                index += 1

            await self.sendEmbed(ctx.channel, title, f'**ROLES PAGE:{page}/{total_pages}**', fields=fields, delete_after=60, footer="**You have 60 seconds to answer**")
            page += 1
        try:
            roleResp = await self.bot.wait_for('message', check=check_user, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, 'Took too long to answer!', delete_after=5)
            return None
        else:
            if roleResp.content.isnumeric():
                idx = int(roleResp.content) - 1
                if idx >= 0 and idx < len(guild_roles):
                    # selected_guild_role = discord.utils.get(ctx.guild.roles, name=guild_roles[idx])
                    selected_guild_role = self.get_by_name_or_id(ctx.guild.roles, guild_roles[idx])
                    if selected_guild_role:
                        await self.sendEmbed(ctx.channel, title, f"You selected the role: '{selected_guild_role.name}'", delete_after=5)

            await roleResp.delete()
        if not selected_guild_role:
            await self.sendEmbed(ctx.channel, title, 'I was unable to verify that role as a valid discord role.', delete_after=5)
            return None
        return selected_guild_role
    async def ask_category(self, ctx):
        if self.isAdmin(ctx):
            def check(m):
                same = m.author.id == ctx.author.id
                return same
            def check_yes_no(m):
                msg = m.content
                return utils.str2bool(msg)
            await self.sendEmbed(ctx.channel, "Voice Channel Setup", f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**", delete_after=60, footer="**You have 60 seconds to answer**")
            try:
                category = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await ctx.channel.send('Took too long to answer!', delete_after=5)
            else:
                found_category = next((x for x in ctx.guild.categories if x.name.lower() == category.content.lower()), None)
                await category.delete()
                if found_category:
                    # found existing with that name.
                    # do you want to create a new one?
                    yes_or_no = False
                    await self.sendEmbed(ctx.channel, "Voice Channel Setup", f"**Found an existing category called '{str(found_category.name.upper())}'. Use that category?\n\nReply: YES or NO.**", delete_after=60, footer="**You have 60 seconds to answer**")
                    try:
                        yes_or_no = await self.bot.wait_for('message', check=check_yes_no, timeout=60.0)
                    except asyncio.TimeoutError:
                        await self.sendEmbed(ctx.channel, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
                    else:
                        if yes_or_no:
                            await yes_or_no.delete()
                            return found_category
                        else:
                            return await ctx.guild.create_category_channel(category.content)
                else:
                    return await ctx.guild.create_category_channel(category.content)
        else:
            return None
        await ctx.message.delete()
    def isInVoiceChannel(self, ctx):
        if isinstance(ctx, discord.Member):
            return ctx.voice.channel is not None
        else:
            return ctx.author.voice.channel is not None
    def isAdmin(self, ctx):
        self.db.open()
        guild_settings = self.db.get_guild_settings(ctx.guild.id)
        admin_role = discord.utils.find(lambda r: r.name.lower() in (s.lower().strip() for s in self.settings.admin_roles), ctx.message.guild.roles)
        is_in_guild_admin_role = False
        # see if there are guild settings for admin role
        if guild_settings:
            guild_admin_role = self.get_by_name_or_id(ctx.guild.roles, guild_settings.admin_role)
            is_in_guild_admin_role = guild_admin_role in ctx.author.roles
        is_in_admin_role = admin_role in ctx.author.roles
        admin_user = str(ctx.author.id) in (str(u) for u in self.settings.admin_users)
        is_bot_owner = str(ctx.author.id) == self.settings.bot_owner

        return is_in_admin_role or admin_user or is_bot_owner or is_in_guild_admin_role

    async def sendEmbed(self, channel, title, message, fields=None, delete_after=None, footer=None):
        embed = discord.Embed(title=title, description=message, color=0x7289da)
        # embed.set_author(name=f"{self.settings['name']}", url=self.settings['url'],
        #                 icon_url=self.settings['icon'])
        if fields is not None:
            for f in fields:
                embed.add_field(name=f['name'], value=f['value'], inline='false')
        if footer is None:
            embed.set_footer(text=f'Developed by {self.settings.author}')
        else:
            embed.set_footer(text=footer)
        await channel.send(embed=embed, delete_after=delete_after)
    async def notify_of_error(self, ctx):
        await self.sendEmbed(ctx.channel, "Something Went Wrong", f'{ctx.author.mention}, There was an error trying to complete your request. The error has been logged. I am very sorry. 😢', delete_after=30)

    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        if isinstance(nameOrId, str):
            return discord.utils.get(iterable, name=str(nameOrId))
        elif isinstance(nameOrId, int):
            return discord.utils.get(iterable, id=int(nameOrId))
        else:
            return None
    async def get_or_fetch_channel(self, channelId: int):
        try:
            if channelId:
                chan = self.bot.get_channel(channelId)
                if not chan:
                    chan = await self.bot.fetch_channel(channelId)
                return chan
            else:
                return  None
        except Exception as ex:
            print(ex)
            return None
    async def get_or_fetch_user(self, userId: int):
        try:
            if userId:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except Exception as ex:
            print(ex)
            return None
    async def get_or_fetch_member(self, guild, userId: int):
        try:
            if userId:
                user = guild.get_member(userId)
                if not user:
                    user = await guild.fetch_member(userId)
                return user
            return None
        except Exception as ex:
            print(ex)
            return None
def setup(bot):
    bot.add_cog(voice(bot))
