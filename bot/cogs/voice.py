import discord
import math
import asyncio
import aiohttp
import json
import datetime
from discord.ext import commands
import traceback
import sqlite3
from urllib.parse import quote
import validators
from discord.ext.commands.cooldowns import BucketType
from time import gmtime, strftime
import os
import glob
import typing
from .lib import utils
from .lib import settings

class EmbedField():
    def __init__(self, name, value):
        self.name = name
        self.value = value

class voice(commands.Cog):
    BITRATE_DEFAULT = 64

    def __init__(self, bot):
        self.settings = settings.Settings()
        self.bot = bot

    async def clean_up_tracked_channels(self, guildID):
        print("Clean up tracked channels")
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        try:
            c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ?", (guildID,))
            voiceChannelSet = c.fetchall()
            for vc in voiceChannelSet:
                textChannelId = None
                voiceChannelId = None
                voiceChannel = None
                if voiceChannelSet:
                    voiceChannelId = vc[0]
                    voiceChannel = self.bot.get_channel(voiceChannelId)

                c.execute("SELECT channelID FROM textChannel WHERE guildID = ? and voiceId = ?", (guildID, voiceChannelId))
                textChannelSet = c.fetchone()

                textChannel = None
                if textChannelSet:
                    textChannelId = textChannelSet[0]
                    textChannel = self.bot.get_channel(textChannelId)

                if voiceChannel:
                    if len(voiceChannel.members) == 0 and len(voiceChannel.voice_states) == 0:
                        print(f"Start Tracked Cleanup: {voiceChannelId}")
                        print(f"Deleting Channel {voiceChannel} because everyone left")
                        c.execute('DELETE FROM voiceChannel WHERE guildID = ? and voiceId = ?', (guildID, voiceChannelId,))
                        c.execute('DELETE FROM textChannel WHERE guildID = ? and channelID = ?', (guildID, textChannelId,))
                        if textChannel:
                            await textChannel.delete()
                        await voiceChannel.delete()
                else:
                    if voiceChannelId is not None:
                        print(f"Unable to find voice channel: {voiceChannelId}")
                        if voiceChannelId:
                            c.execute('DELETE FROM voiceChannel WHERE guildID = ? and voiceId = ?', (guildID, voiceChannelId,))
                        if textChannelId:
                            c.execute('DELETE FROM textChannel WHERE guildID = ? and channelID = ?', (guildID, textChannelId,))
        except discord.errors.NotFound as nf:
            print(nf)
            traceback.print_exc()
            print("Channel Not Found. Already Cleaned Up")
        finally:
             conn.commit()
             conn.close()

    @commands.group()
    async def voice(self, ctx):
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.clean_up_tracked_channels(guild.id)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        try:
            if before and after:
                if after.type == discord.ChannelType.voice:
                    if before.id == after.id:
                        # This handles a manual channel rename. it changes the text channel name to match.
                        guildID = before.guild.id or after.guild.id
                        c.execute("SELECT userID FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildID, after.id,))
                        trackedSet = c.fetchone()
                        category_id = after.category.id
                        if trackedSet:
                            channelOwnerId = int(trackedSet[0])
                            if before.name == after.name:
                                # same name. ignore
                                print(f"Channel Names are the same. Nothing to do")
                                pass
                            else:

                                c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (channelOwnerId, guildID,))
                                userSettings = c.fetchone()
                                c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
                                guildSettings = c.fetchone()
                                if userSettings:
                                    default_role = userSettings[3]
                                else:
                                    if guildSettings:
                                        default_role = guildSettings[3] or self.settings.default_role
                                    else:
                                        default_role = self.settings.default_role


                                # new channel name
                                c.execute("SELECT channelID from textChannel WHERE guildID = ? AND voiceID = ?", (guildID, after.id))
                                textSet = c.fetchone()
                                textChannel = None
                                if textSet:
                                    textChannel = self.bot.get_channel(int(textSet[0]))
                                if textChannel:
                                    print(f"Change Text Channel Name: {after.name}")
                                    await textChannel.edit(name=after.name)
                                    await self.sendEmbed(textChannel, "Updated Channel Name", f'You have changed the channel name to {textChannel.name}!', delete_after=5)
                                c.execute("SELECT channelName FROM userSettings WHERE userID = ? AND guildID = ?", (channelOwnerId, guildID,))
                                voiceGroup = c.fetchone()
                                if voiceGroup is None:
                                    c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?, ?)", (guildID, channelOwnerId, after.name, 0, self.BITRATE_DEFAULT, default_role))
                                else:
                                    c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (after.name, channelOwnerId, guildID,))
        except Exception as e:
            print(e)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        print("On Voice State Update")
        guildID = member.guild.id
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        await self.clean_up_tracked_channels(guildID)
        await asyncio.sleep(2)
        c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
        voiceChannels = [item for clist in c.fetchall() for item in clist]
        if voiceChannels is None:
            print(f"No voice channel found for GuildID: {guildID}")
            pass
        else:
            try:
                print("Check for user in Create Channel")
                if after.channel is not None and after.channel.id in voiceChannels:
                    # User Joined the CREATE CHANNEL
                    print(f"User requested to CREATE CHANNEL")
                    category_id = after.channel.category_id
                    c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (member.id, guildID))
                    userSettings = c.fetchone()
                    c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
                    guildSettings = c.fetchone()

                    # CHANNEL SETTINGS START
                    limit = 0
                    locked = False
                    bitrate = self.BITRATE_DEFAULT
                    name = f"{member.name}'s Channel"
                    default_role = self.settings.default_role
                    if userSettings is None:
                        if guildSettings is not None:
                            limit = guildSettings[0]
                            locked = guildSettings[1]
                            bitrate = guildSettings[2]
                            default_role = guildSettings[3] or self.settings.default_role
                    else:
                        name = userSettings[0]
                        if guildSettings is None:
                            limit = userSettings[1]
                            bitrate = userSettings[2]
                            default_role = userSettings[3] or self.settings.default_role
                            locked = False
                        elif guildSettings is not None:
                            limit = userSettings[1]
                            if userSettings[1] == 0:
                                limit =  guildSettings[0]
                            locked = guildSettings[1] or False
                            bitrate = userSettings[2] or guildSettings[2]
                            default_role = userSettings[3] or guildSettings[3] or self.settings.default_role
                        else:
                            limit = userSettings[1]
                            locked = guildSettings[1]
                            bitrate = guildSettings[2]
                            default_role = guildSettings[3] or self.settings.default_role
                    # CHANNEL SETTINGS END

                    mid = member.id
                    category = self.bot.get_channel(category_id)
                    print(f"Creating channel {name} in {category} with bitrate {bitrate}kbps")
                    voiceChannel = await member.guild.create_voice_channel(name, category=category, reason="Create Channel Request by {member}")
                    textChannel = await member.guild.create_text_channel(name, category=category)
                    channelID = voiceChannel.id

                    print(f"Moving {member} to {voiceChannel}")
                    await member.move_to(voiceChannel)
                    # if the bot cant do this, dont fail...
                    try:
                        print(f"Setting permissions on {voiceChannel}")
                        await voiceChannel.set_permissions(member, speak=True, priority_speaker=True, connect=True, read_messages=True, send_messages=True, view_channel=True, stream=True)
                        await textChannel.set_permissions(member, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    except Exception as ex:
                        print(ex)
                        traceback.print_exc()
                    print(f"Set user limit to {limit} on {voiceChannel}")
                    await voiceChannel.edit(name=name, user_limit=limit, bitrate=(bitrate*1000))
                    print(f"Track voiceChannel {mid},{channelID}")
                    print(f"Track Voice and Text Channels {name} in {category}")
                    c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildID, mid, channelID,))
                    c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildID, mid, textChannel.id, channelID,))
                    conn.commit()

                    sec_role = default_role or self.settings.default_role
                    role = discord.utils.get(member.guild.roles, name=sec_role)
                    try:
                        print(f"Check if bot can set channel for {sec_role} {voiceChannel}")
                        await textChannel.set_permissions(role, read_messages=(not locked), send_messages=(not locked), read_message_history=(not locked), view_channel=(not locked))
                        await voiceChannel.set_permissions(role, speak=True, connect=(not locked), read_messages=(not locked), send_messages=(not locked), view_channel=(not locked), stream=(not locked))
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
            finally:
                conn.close()

    @voice.command()
    async def version(self, ctx):
        appName = utils.dict_get(self.settings.__dict__, "name", default_value = "Voice Create Bot")
        await self.sendEmbed(ctx.channel, "Version Information", f"Voice Create Bot Version: {self.settings.APP_VERSION}", delete_after=10)
        await ctx.message.delete()

    @voice.command()
    async def channels(self, ctx):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        mid = ctx.author.id
        guildID = ctx.author.guild.id
        try:
            if self.isAdmin(ctx):
                c.execute("SELECT voiceID, userID FROM voiceChannel WHERE guildID = ?", (guildID,))
                voiceSets = c.fetchall()
                channelFields = list()
                for v in voiceSets:
                    channel = self.bot.get_channel(int(v[0]))
                    user = self.bot.get_user(int(v[1]))
                    textChannel = None
                    c.execute("SELECT channelID FROM textChannel WHERE guildID = ? and voiceID = ?", (guildID, channel.id,))
                    textSet = c.fetchone()
                    tchanName = f"**[No Text Channel]**"
                    if textSet:
                        textChannel = self.bot.get_channel(int(textSet[0]))
                        if textChannel:
                            tchanName = f"#{textChannel.name}"
                    chanName = f"**[Unknown Channel: {str(v[0])}]**"
                    if channel:
                         chanName = channel.name
                    userName = f"**[Unknown User: {str(v[1])}]**"
                    if user:
                        userName = f"{user.name}#{user.discriminator}"
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
        finally:
            conn.close()
            await ctx.message.delete()

    @voice.command(aliases=["track-text-channel", "ttc"])
    async def track_text_channel(self, ctx, channel: discord.TextChannel = None):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        mid = ctx.author.id
        guildID = ctx.author.guild.id

        try:
            if self.isAdmin(ctx):

                voiceChannel = None
                if ctx.author.voice:
                    voiceChannel = ctx.author.voice.channel

                if channel is None:
                    await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, You must specific a channel to track.", fields=None, delete_after=5)
                    conn.close()
                    await ctx.message.delete()
                    return

                if voiceChannel:
                    # check if this voice channel is tracked.
                    c.execute("SELECT voiceID FROM voiceChannel WHERE voiceID = ? and guildID = ?", (voiceChannel.id, guildID,))
                    voiceGroup = c.fetchone()
                    if voiceGroup:
                        c.execute("SELECT channelID FROM textChannel WHERE voiceID = ? and guildID = ?", (voiceChannel.id, guildID,))
                        textGroup = c.fetchone()
                        if not textGroup:
                            # we can add this channel as it is not tracked.
                            # if it lives in the same category (as a safety measure)
                            if channel.category_id == voiceChannel.category_id:
                                # `guildID` INTEGER, `userID` INTEGER, `channelID` INTEGER, `voiceID` INTEGER
                                c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildID, mid, channel.id, voiceChannel.id,))
                                conn.commit()
                                await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, I am now tracking '{channel}' with '{voiceChannel}'.", fields=None, delete_after=5)
                            else:
                                # not in the same category
                                await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, {channel} is in a different category than '{voiceChannel}'. Tracking this channel is not supported.", fields=None, delete_after=5)
                        else:
                            # channel already has a textChannel associated with it.
                            await self.sendEmbed(ctx.channel, "Track Text Channel", f"{ctx.author.mention}, The voice channel '{voiceChannel}' already has a channel associated with it", fields=None, delete_after=5)
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
        finally:
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def track(self, ctx):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        mid = ctx.author.id
        guildID = ctx.author.guild.id

        channel = None
        try:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            if channel is None:
                await self.sendEmbed(ctx.channel, "Track Channel", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
            else:
                if self.isAdmin(ctx):
                    c.execute("SELECT voiceID FROM voiceChannel WHERE voiceID = ?", (channel.id,))
                    voiceGroup = c.fetchone()
                    if voiceGroup:
                        await self.sendEmbed(ctx.channel, "Track Channel", f"{ctx.author.mention} This channel is already tracked.", delete_after=5)
                    else:
                        c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildID, mid, channel.id,))
                        conn.commit()
                        await self.sendEmbed(ctx.channel, "Track Channel", f"{ctx.author.mention} The channel '{channel.name}' is now tracked.\n\nUse the `.voice track-text-channel #channel-name` command to track the associated text channel.", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def owner(self, ctx, member: discord.Member):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        channel = None
        try:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            if channel is None:
                await self.sendEmbed(ctx.channel, "Set Channel Owner", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
            else:
                aid = ctx.author.id
                c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel.id,))
                voiceGroup = c.fetchone()
                if voiceGroup is None:
                    await self.sendEmbed(ctx.channel, "Set Channel Owner", f"{ctx.author.mention} That channel is not managed by me. I can't help you own that channel.", delete_after=5)
                else:
                    if self.isAdmin(ctx) or ctx.author.id == voiceGroup[0]:
                        await self.sendEmbed(ctx.channel, "Channel Owner Updated", f"{ctx.author.mention}, {member.mention} is now the owner of the channel.", delete_after=5)
                        c.execute("UPDATE voiceChannel SET userID = ? WHERE voiceID = ?", (member.id, channel.id))
                    else:
                        await self.sendEmbed(ctx.channel, "Set Channel Owner", f"{ctx.author.mention}, You do not have permission to set the owner of the channel. If the owner left, try `claim`.", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def resync(self, ctx):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Channel Sync", f'{ctx.author.mention} You do not own this channel, and do not have permissions to resync it.', delete_after=5)
                return
            c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
            userSettings = c.fetchone()
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            if userSettings:
                default_role = userSettings[3]
            else:
                if guildSettings:
                    default_role = guildSettings[3] or self.settings.default_role
                else:
                    default_role = self.settings.default_role
            everyone = discord.utils.get(ctx.guild.roles, name=default_role)

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? and guildID = ?", (aid, guildID, ))
            voiceGroup = c.fetchone()
            if voiceGroup is None or not channel_id:
                await self.sendEmbed(ctx.channel, "Channel Sync", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                channel = self.bot.get_channel(channelID)

                c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channelID))
                textGroup = c.fetchone()
                textChannel = None
                if channel:
                    if textGroup:
                        textChannel = self.bot.get_channel(textGroup[0])
                        await textChannel.edit(sync_permissions=True)
                        await textChannel.set_permissions(ctx.author, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    await channel.edit(sync_permissions=True)
                    await channel.set_permissions(ctx.author, speak=True, priority_speaker=True, connect=True, read_messages=True, send_messages=True, view_channel=True, stream=True)
                await self.sendEmbed(ctx.channel, "Channel Sync", f'{ctx.author.mention} The permissions of this channel have been resync\'d with the defaults.', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def private(self, ctx):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Channel Private", f'{ctx.author.mention} You do not own this channel, and do not have permissions to make it private.', delete_after=5)
                return

            c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
            userSettings = c.fetchone()
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            if userSettings:
                default_role = userSettings[3]
            else:
                if guildSettings:
                    default_role = guildSettings[3] or self.settings.default_role
                else:
                    default_role = self.settings.default_role
            everyone = discord.utils.get(ctx.guild.roles, name=default_role)

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? and guildID = ?", (aid, guildID, ))
            voiceGroup = c.fetchone()
            if voiceGroup is None or not channel_id:
                await self.sendEmbed(ctx.channel, "Channel Private", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                channel = self.bot.get_channel(channelID)

                c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channelID))
                textGroup = c.fetchone()
                textChannel = None
                if channel:

                    await self.sendEmbed(ctx.channel, "Channel Private", f'{ctx.author.mention}, I am assigning permissions. This may take a moment.', delete_after=5)
                    permRoles = []
                    for m in channel.members:
                        if m.id != aid:
                            permRoles.append(m)
                    denyRoles = [everyone]
                    for gr in ctx.guild.roles:
                        denyRoles.append(gr)
                    if textGroup:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel:
                        await textChannel.edit(sync_permissions=True)
                        await textChannel.set_permissions(ctx.message.author, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                        for r in permRoles:
                            await textChannel.set_permissions(r, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                        # deny everyone else
                        for r in denyRoles:
                            await textChannel.set_permissions(r, connect=False, read_messages=False, view_channel=False, read_message_history=False, send_messages=False)

                    await channel.edit(sync_permissions=True)
                    await channel.set_permissions(ctx.message.author, speak=True, view_channel=True, connect=True, use_voice_activation=False, stream=False )
                    for r in permRoles:
                        await channel.set_permissions(r, speak=True, view_channel=True, connect=True, use_voice_activation=False, stream=False)
                    # deny everyone else
                    for r in denyRoles:
                        await channel.set_permissions(r, speak=False, view_channel=False, connect=False)

                await self.sendEmbed(ctx.channel, "Channel Private", f'{ctx.author.mention} This channel is locked for just the people in this channel.', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def mute(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Channel Mute", f'{ctx.author.mention} You do not own this channel, and do not have permissions to mute it.', delete_after=5)
                return

            c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
            userSettings = c.fetchone()
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            if userSettings:
                default_role = userSettings[3]
            else:
                if guildSettings:
                    default_role = guildSettings[3] or self.settings.default_role
                else:
                    default_role = self.settings.default_role

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? and guildID = ?", (aid, guildID, ))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await self.sendEmbed(ctx.channel, "Channel Mute", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                everyone = discord.utils.get(ctx.guild.roles, name=default_role)
                channel = self.bot.get_channel(channelID)


                c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channelID))
                textGroup = c.fetchone()
                textChannel = None
                if channel:
                    permRoles = [everyone]
                    if userOrRole:
                        permRoles.append(userOrRole)

                    if textGroup:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel:
                        await textChannel.set_permissions(ctx.message.author, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                        for r in permRoles:
                            await textChannel.set_permissions(r, send_messages=False)

                    await channel.set_permissions(ctx.message.author, speak=True)
                    for r in permRoles:
                        await channel.set_permissions(r, speak=False)

                await self.sendEmbed(ctx.channel, "Channel Mute", f'{ctx.author.mention} All users in the specified role are now muted 🔇', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def unmute(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Channel Unmute", f'{ctx.author.mention} You do not own this channel, and do not have permissions to unmute it.', delete_after=5)
                return

            c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
            userSettings = c.fetchone()
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            if userSettings:
                default_role = userSettings[3]
            else:
                if guildSettings:
                    default_role = guildSettings[3] or self.settings.default_role
                else:
                    default_role = self.settings.default_role

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? and guildID = ?", (aid, guildID, ))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await self.sendEmbed(ctx.channel, "Channel Unmute", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                everyone = discord.utils.get(ctx.guild.roles, name=default_role)
                channel = self.bot.get_channel(channelID)

                c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channelID))
                textGroup = c.fetchone()
                textChannel = None
                if channel:

                    permRoles = [everyone]
                    if userOrRole:
                        permRoles.append(userOrRole)

                    if textGroup:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel:
                        await textChannel.set_permissions(ctx.message.author, connect=True, read_messages=True, send_messages=True, read_message_history=True, view_channel=True)
                        for r in permRoles:
                            await textChannel.set_permissions(r, send_messages=True)

                    await channel.set_permissions(ctx.message.author, speak=True, connect=True, read_messages=True, send_messages=True, view_channel=True)
                    for r in permRoles:
                        await channel.set_permissions(r, speak=True)

                await self.sendEmbed(ctx.channel, "Channel Unmute", f'{ctx.author.mention} All users in the specified role are now unmuted 🔊', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
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
            chunked = utils.chunk_list(list(command_list.keys()), 10)
            pages = math.ceil(len(command_list) / 10)
            page = 1
            for chunk in chunked:
                fields = list()
                for k in chunk:
                    cmd = command_list[k.lower()]
                    if cmd['admin']:
                        if self.isAdmin(ctx) :
                            fields.append({"name": cmd['help'], "value": f"`{cmd['usage']}`"})
                            fields.append({"name": "More Help", "value": f"`.voice help {k.lower()}`"})
                            fields.append({"name": "Admin Command", "value": f"Can only be ran by a server admin"})
                    else:
                        fields.append({"name": cmd['help'], "value": f"`{cmd['usage']}`"})
                        fields.append({"name": "More Help", "value": f"`.voice help {k.lower()}`"})

                await self.sendEmbed(ctx.channel, f"Voice Bot Command Help ({page}/{pages})", "List of Available Commands", fields=fields)
                page += 1
        await ctx.message.delete()

    @voice.command(pass_context=True)
    async def setup(self, ctx):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        guildID = ctx.guild.id
        try:
            print(f"User id triggering setup: {ctx.author.id}")
            aid = ctx.author.id
            # If the person is the OWNER or an ADMIN
            if self.isAdmin(ctx):
                def check(m):
                    return m.author.id == ctx.author.id
                # Ask them for the category name
                category = await self.ask_category(ctx)
                await self.sendEmbed(ctx.channel, "Voice Channel Setup", '**Enter the name of the voice channel: (e.g Join To Create)**', delete_after=60, footer="**You have 60 seconds to answer**")
                try:
                    channel = await self.bot.wait_for('message', check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await self.sendEmbed(ctx.channel, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
                else:
                    try:
                        channel = await ctx.guild.create_voice_channel(channel.content, category=category)
                        c.execute("SELECT * FROM guild WHERE guildID = ? AND ownerID=? AND voiceChannelID=?", (guildID, aid, channel.id))
                        voiceGroup = c.fetchone()
                        if voiceGroup is None:
                            c.execute("INSERT INTO guild VALUES (?, ?, ?, ?)", (guildID, aid, channel.id, category.id))
                        else:
                            c.execute("UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?", (
                                guildID, aid, channel.id, category.id, guildID))
                        await ctx.channel.send("**You are all setup and ready to go!**", delete_after=5)
                    except Exception as e:
                        traceback.print_exc()
                        await self.sendEmbed(ctx.channel, "Voice Channel Setup", "You didn't enter the names properly.\nUse `.voice setup` again!", delete_after=5)
            else:
                await self.sendEmbed(ctx.channel, "Voice Channel Setup", f"{ctx.author.mention} only the owner or admins of the server can setup the bot!", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @setup.error
    async def info_error(self, ctx, error):
        print(error)
        traceback.print_exc()

    @voice.command(aliases=['set-default-role', 'sdr'])
    async def set_default_role(self, ctx, default_role: discord.Role):
        if self.isAdmin(ctx):
            guildID = ctx.guild.id
            conn = sqlite3.connect(self.settings.db_path)
            c = conn.cursor()
            try:
                category = await self.set_role_ask_category(ctx)
                if category:
                    print(category)
                    c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category.id,))
                    guildSettings = c.fetchone()
                    if guildSettings:
                        c.execute("UPDATE guildCategorySettings SET defaultRole = ? WHERE WHERE guildID = ? and voiceCategoryID = ?", (default_role, guildID, category.id))
                    else:
                        await self.sendEmbed(ctx.channel, "Channel Category Settings", f"Existing settings not found. Use `.voice settings` to configure.", fields=None, delete_after=5)
                else:
                    print("no category found")
            except Exception as e:
                print(ex)
                trackback.print_exc()
            finally:
                conn.commit()
                conn.close()
                # await ctx.message.delete()



    @voice.command()
    async def settings(self, ctx, category: str, locked: str = "False", limit: int = 0, bitrate: int = 64, default_role: discord.Role = None):
        if self.isAdmin(ctx):
            conn = sqlite3.connect(self.settings.db_path)
            c = conn.cursor()
            try:
                found_category = next((x for x in ctx.guild.categories if x.name == category), None)
                if found_category:
                    bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))
                    bitrate_min = 8
                    br = int(bitrate)

                    if br > bitrate_limit:
                        br = bitrate_limit
                    elif br < bitrate_min:
                        br = bitrate_min
                    new_default_role = default_role
                    if not new_default_role:
                        new_default_role = self.settings.default_role
                    c.execute("SELECT channelLimit, channelLocked, defaultRole FROM guildCategorySettings WHERE guildID = ? AND voiceCategoryID = ?", (ctx.guild.id, found_category.id,))
                    catSettings = c.fetchone()
                    if catSettings:
                        new_default_role = catSettings[3] or self.settings.default_role
                        print(f"UPDATE category settings")
                        c.execute("UPDATE guildCategorySettings SET channelLimit = ?, channelLocked = ? WHERE guildID = ? AND channelLimit = ? AND bitrate = ? AND defaultRole = ?",
                            (int(limit), utils.str2bool(locked), ctx.guild.id, found_category.id, int(br), new_default_role.name,))
                    else:
                        print(f"INSERT category settings")
                        c.execute("INSERT INTO guildCategorySettings VALUES ( ?, ?, ?, ?, ?, ? )", (ctx.guild.id, found_category.id, int(limit), utils.str2bool(locked), int(br), new_default_role.name,))
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
                        "value": f"{new_default_role}"
                    })

                    await self.sendEmbed(ctx.channel, "Channel Category Settings", f"Category '{category}' settings have been set.", fields=embed_fields, delete_after=5)

                else:
                    print(f"No Category found for '{category}'")
            except Exception as ex:
                print(ex)
                traceback.print_exc()
            finally:
                conn.commit()
                conn.close()
        else:
            await self.sendEmbed(ctx.channel, "Channel Category Settings", f"{ctx.author.mention} only the owner or admins of the server can setup the bot!", delete_after=5)
        await ctx.message.delete()

    @voice.command()
    async def cleandb(self,ctx):
        if self.isAdmin(ctx):
            conn = sqlite3.connect(self.settings.db_path)
            guildID = ctx.guild.id
            try:
                c = conn.cursor()
                c.execute("DELETE FROM `userSettings` WHERE guildID = ?", (guildID, ))
                conn.commit()
                await self.sendEmbed(ctx.channel, "Clean Database", "All User Settings have been purged from database.", delete_after=5)
            except Exception as ex:
                print(ex)
                traceback.print_exc()
            finally:
                conn.close()
        await ctx.message.delete()

    @voice.command()
    async def reset(self,ctx, user: discord.Member = None):
        dataUser = ctx.author
        if user and self.isAdmin(ctx):
            dataUser = user

        conn = sqlite3.connect(self.settings.db_path)
        guildID = ctx.guild.id
        try:
            c = conn.cursor()
            c.execute("DELETE FROM `userSettings` WHERE guildID = ? AND userID = ?", (guildID, dataUser.id,))
            conn.commit()
            await self.sendEmbed(ctx.channel, "Reset User Settings", f"User Settings for '{dataUser.mention}' has been purged from database.", delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.close()
        await ctx.message.delete()

    @voice.command()
    async def lock(self, ctx, role: discord.Role = None):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Channel Lock", f'{ctx.author.mention} You do not own this channel, and do not have permissions to lock it.', delete_after=5)
                return

            c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
            userSettings = c.fetchone()
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            if userSettings:
                default_role = userSettings[3]
            else:
                if guildSettings:
                    default_role = guildSettings[3] or self.settings.default_role
                else:
                    default_role = self.settings.default_role
            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? and guildID = ?", (aid, guildID, ))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await self.sendEmbed(ctx.channel, "Channel Lock", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                everyone = discord.utils.get(ctx.guild.roles, name=default_role)
                channel = self.bot.get_channel(channelID)

                c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channelID))
                textGroup = c.fetchone()
                textChannel = None
                if channel:
                    if textGroup:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel:
                        await textChannel.set_permissions(ctx.message.author, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=False)
                        await textChannel.set_permissions(everyone, read_messages=False,send_messages=False, view_channel=False, read_message_history=False)

                    await channel.set_permissions(ctx.message.author, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    await channel.set_permissions(everyone, connect=False, view_channel=False, stream=False)
                    if role:
                        await channel.set_permissions(role, connect=False, read_messages=False, send_messages=False, view_channel=False, stream=False)
                        if textChannel:
                            await textChannel.set_permissions(role, read_messages=False,send_messages=False, view_channel=False, read_message_history=False)

                await self.sendEmbed(ctx.channel, "Channel Lock", f'{ctx.author.mention} Voice chat locked! 🔒', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def unlock(self, ctx, role: discord.Role = None):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Channel Unlock", f'{ctx.author.mention} You do not own this channel, and do not have permissions to unlock it.', delete_after=5)
                return

            c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
            userSettings = c.fetchone()
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            if userSettings:
                default_role = userSettings[3]
            else:
                if guildSettings:
                    default_role = guildSettings[3] or self.settings.default_role
                else:
                    default_role = self.settings.default_role

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? and guildID = ?", (aid, guildID,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await self.sendEmbed(ctx.channel, "Channel Unlock", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                everyone = discord.utils.get(ctx.guild.roles, name=default_role)
                channel = self.bot.get_channel(channelID)

                c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channelID))
                textGroup = c.fetchone()
                textChannel = None
                if channel:
                    if textGroup:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel:
                        await textChannel.set_permissions(ctx.message.author, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=False)
                        await textChannel.set_permissions(everyone, read_messages=True,send_messages=True, view_channel=True, read_message_history=True)

                    await channel.set_permissions(ctx.message.author, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    await channel.set_permissions(everyone, connect=True, view_channel=True, stream=True)
                    if role:
                        await channel.set_permissions(role, connect=True, read_messages=True, send_messages=True, view_channel=None, stream=True)
                        if textChannel:
                            await textChannel.set_permissions(role, read_messages=True,send_messages=True, view_channel=True, read_message_history=True)

                await self.sendEmbed(ctx.channel, "Channel Unlock", f'{ctx.author.mention} Voice chat unlocked! 🔓', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command(aliases=["allow"])
    async def permit(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Grant User Access", f'{ctx.author.mention} You do not own this channel, and do not have permissions to allow access.', delete_after=5)
                return

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await self.sendEmbed(ctx.channel, "Grant User Access", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                channel = self.bot.get_channel(channelID)

                c.execute("SELECT channelID from textChannel WHERE voiceID = ?", (channelID,))
                textSet = c.fetchone()
                if textSet:
                    textChannelID = textSet[0]
                    textChannel = self.bot.get_channel(textChannelID)
                    if textChannel:
                        if userOrRole:
                            await textChannel.set_permissions(userOrRole, read_messages=True, send_messages=True, view_channel=True, read_message_history=True, )
                if userOrRole:
                    await channel.set_permissions(userOrRole, connect=True, view_channel=True, speak=True, stream=True)
                    await self.sendEmbed(ctx.channel, "Grant User Access", f'{ctx.author.mention} You have permitted {userOrRole.name} to have access to the channel. ✅', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx, userOrRole: typing.Union[discord.Role, discord.Member] = None):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Reject User Access", f'{ctx.author.mention} You do not own this channel, and do not have permissions to deny access.', delete_after=5)
                return

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await self.sendEmbed(ctx.channel, "Reject User Access", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                channel = self.bot.get_channel(channelID)

                c.execute("SELECT channelID from textChannel WHERE voiceID = ?", (channelID,))
                textSet = c.fetchone()
                if textSet:
                    textChannelID = textSet[0]
                    textChannel = self.bot.get_channel(textChannelID)
                    if textChannel:
                        if userOrRole:
                            await textChannel.set_permissions(userOrRole, read_messages=False, send_messages=False, view_channel=False, read_message_history=False)


                if userOrRole:
                    for m in channel.members:
                        if m.id != aid:
                            if m.id == userOrRole.id:
                                m.disconnect()
                            if m.has_role(userOrRole):
                                m.disconnect()

                    await channel.set_permissions(userOrRole, connect=False, read_messages=False, view_channel=False, speak=False, stream=False, read_message_history=False)
                    await self.sendEmbed(ctx.channel, "Reject User Access", f'{ctx.author.mention} You have rejected {userOrRole} from accessing the channel. ❌', delete_after=5)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def limit(self, ctx, limit):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Set Channel Limit", f'{ctx.author.mention} You do not own this channel, and do not have permissions to set the channel limit.', delete_after=5)
                return

            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            default_role = self.settings.default_role
            if guildSettings:
                default_role = guildSettings[3] or self.settings.default_role

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? AND guildID = ?", (aid, guildID,))
            voiceGroup = c.fetchone()
            if voiceGroup is None and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Set Channel Limit", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceGroup[0]
                channel = self.bot.get_channel(channelID)

                await channel.edit(user_limit=limit)
                await self.sendEmbed(ctx.channel, "Set Channel Limit", f'{ctx.author.mention} You have set the channel limit to be ' + '{}!'.format(limit), delete_after=5)
                c.execute("SELECT channelName FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
                voiceGroup = c.fetchone()
                if voiceGroup is None:
                    c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?, ?)",(ctx.guild.id, aid, f"{ctx.author.name}'s Channel'", limit, self.BITRATE_DEFAULT, default_role))
                else:
                    c.execute("UPDATE userSettings SET channelLimit = ? WHERE userID = ? AND guildID = ?", (limit, aid, guildID,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def bitrate(self, ctx, bitrate: int = 64):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))
        bitrate_min = 8
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            # get the channel owner, in case this is an admin running the command.
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Set Channel Limit", f'{ctx.author.mention} You do not own this channel, and do not have permissions to set the channel limit.', delete_after=5)
                return
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            default_role = self.settings.default_role
            if guildSettings:
                default_role = guildSettings[3] or self.settings.default_role
            print(f"Bitrate Limit: {bitrate_limit}")
            br_set = int(bitrate)

            if br_set > bitrate_limit:
                await self.sendEmbed(ctx.channel, "Updated Channel Bitrate", f"{ctx.author.mention}, your bitrate is above the bitrate limit of {bitrate_limit}kbps. I will apply the the limit instead.", delete_after=5)
                br_set = bitrate_limit
            elif br_set < bitrate_min:
                await self.sendEmbed(ctx.channel, "Updated Channel Bitrate", f"{ctx.author.mention}, your bitrate is below the bitrate minimum of {bitrate_min}kbps. I will apply the the minimum instead.", delete_after=5)

                br_set = bitrate_min

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? AND guildID = ?", (aid, guildID,))
            voiceGroup = c.fetchone()
            if voiceGroup is None and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Updated Channel Bitrate", f"{ctx.author.mention}, you don't own a channel.", delete_after=5)
            else:
                channelID = ctx.author.voice.channel.id
                channel = self.bot.get_channel(channelID)
                br = br_set * 1000
                await channel.edit(bitrate=br)
                await self.sendEmbed(ctx.channel, "Updated Channel Bitrate", f'{ctx.author.mention}, you have set the channel bitrate to be ' + '{}kbps!'.format(br_set), delete_after=5)
                # see if we have user settings
                c.execute("SELECT channelName FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
                voiceGroup = c.fetchone()
                if voiceGroup is None:
                    c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?, ?)", (ctx.guild.id, aid, f"{ctx.author.name}'s Channel", 0, br_set, default_role))
                else:
                    c.execute("UPDATE userSettings SET bitrate = ? WHERE userID = ? AND guildID = ?", (br_set, aid, guildID,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def name(self, ctx, *, name):
        channel_id = None
        if self.isInVoiceChannel(ctx):
            channel_id = ctx.author.voice.channel.id
        else:
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return

        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        voiceChannel = ctx.author.voice.channel
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        try:
            # get the channel owner, in case this is an admin running the command.
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel_id,))
            channelOwnerGroup = c.fetchone()
            if channelOwnerGroup:
                if channelOwnerGroup[0] != aid:
                    aid = channelOwnerGroup[0]
            if not self.isAdmin(ctx) and ctx.author.id != aid:
                await self.sendEmbed(ctx.channel, "Set Channel Limit", f'{ctx.author.mention} You do not own this channel, and do not have permissions to set the channel limit.', delete_after=5)
                return

            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
            guildSettings = c.fetchone()
            default_role = self.settings.default_role
            if guildSettings:
                default_role = guildSettings[3] or self.settings.default_role

            c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? AND guildID = ?", (aid, guildID,))
            voiceGroup = c.fetchone()
            if voiceGroup is None and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Updated Channel Name", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
            else:
                channelID = voiceChannel.id
                c.execute("SELECT channelID FROM textChannel WHERE guildID = ? AND voiceID = ?", (guildID, channelID))
                textGroup = c.fetchone()
                c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ? AND guildID = ?", (channelID, guildID,))
                voiceSet = c.fetchone()
                channelOwnerID = aid
                if voiceSet is not None:
                    channelOwnerID = voiceSet[0] or aid
                textChannel = None
                channel = self.bot.get_channel(channelID)
                if channel is not None:

                    if textGroup is not None:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel is not None:
                        print(f"Change Text Channel Name from Command")
                        await textChannel.edit(name=name)

                    await channel.edit(name=name)
                    await self.sendEmbed(ctx.channel, "Updated Channel Name", f'You have changed the channel name to {name}!', delete_after=5)
                    c.execute("SELECT channelName FROM userSettings WHERE userID = ? AND guildID = ?", (channelOwnerID, guildID,))
                    voiceGroup = c.fetchone()
                    if voiceGroup is None:
                        c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?, ?)", (guildID, channelOwnerID, name, 0, self.BITRATE_DEFAULT, default_role))
                    else:
                        c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (name, channelOwnerID, guildID,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command(aliases=["rename"])
    async def force_name(self, ctx, *, name):
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        category_id = ctx.channel.category.id
        try:
            if self.isAdmin(ctx):
                c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
                guildSettings = c.fetchone()
                default_role = self.settings.default_role
                if guildSettings:
                    default_role = guildSettings[3] or self.settings.default_role
                channelID = voiceGroup[0]
                c.execute("SELECT channelID FROM textChannel WHERE guildID = ? AND voiceID = ?", (guildID, channelID))
                textGroup = c.fetchone()
                textChannel = None
                channel = self.bot.get_channel(channelID)
                if channel is not None:

                    c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ? AND guildID = ?", (channelID, guildID,))
                    channelOwner = c.fetchone()

                    if textGroup is not None:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel is not None:
                        await textChannel.edit(name=name)

                    await channel.edit(name=name)
                    await self.sendEmbed(ctx.channel, "Updated Channel Name", f'You have changed the channel name to {name}!', delete_after=5)
                    c.execute("SELECT channelName FROM userSettings WHERE userID = ? AND guildID = ?", (channelOwner, guildID,))
                    voiceGroup = c.fetchone()
                    if voiceGroup is None:
                        c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?, ?)", (guildID, channelOwner, name, 0, self.BITRATE_DEFAULT, default_role))
                    else:
                        c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (name, channelOwner, guildID,))
            else:
                print(f"{ctx.author} tried to run command 'rename'")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def whoowns(self, ctx):
        try:
            conn = sqlite3.connect(self.settings.db_path)
            c = conn.cursor()
            guildID = ctx.guild.id
            channel = ctx.author.voice.channel
            if channel == None:
                await self.sendEmbed(ctx.channel, "Who Owns Channel", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
            else:
                c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ? AND guildID = ?", (channel.id, guildID,))
                voiceGroup = c.fetchone()
                if voiceGroup is not None:
                    owner = ctx.guild.get_member(voiceGroup[0])
                    await self.sendEmbed(ctx.channel, "Who Owns Channel", f"{ctx.author.mention} The channel '{channel.name}' is owned by {owner.mention}!", delete_after=30)
            conn.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            await ctx.message.delete()

    @voice.command()
    async def give(self, ctx, newOwner: discord.Member):
        """Give ownership of the channel to another user in the channel"""
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        guildID = ctx.guild.id
        if not self.isInVoiceChannel(ctx):
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            channel = ctx.author.voice.channel
            channel_id = ctx.author.voice.channel.id
            aid = ctx.author.id
            noID = newOwner.id
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ? AND guildID = ?", (channel_id, guildID,))
            ownerID = c.fetchone()
            if ownerID is None and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Change Channel Owner", f"{ctx.author.mention} You don't own the channel you are in.", delete_after=5)
            else:
                if noID == ownerID:
                    # Can't grant to self
                    await self.sendEmbed(ctx.channel, "Change Channel Owner", f"{ctx.author.mention} You already own this channel.", delete_after=5)
                else:
                    c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (ownerID[0], guildID, channel_id))
                    textGroup = c.fetchone()
                    if textGroup is not None:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel is not None:
                        c.execute("UPDATE textChannel SET userID = ? WHERE voiceID = ? AND guildID = ?",(noID, channel_id, guildID,))

                    await self.sendEmbed(ctx.channel, "Updated Channel Owner", f"{ctx.author.mention}, {newOwner.mention} is now the owner of '{channel.name}'!", delete_after=5)
                    c.execute("UPDATE voiceChannel SET userID = ? WHERE voiceID = ? AND guildID = ?", (noID, channel_id, guildID,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    async def claim(self, ctx):
        x = False
        conn = sqlite3.connect(self.settings.db_path)
        c = conn.cursor()
        guildID = ctx.guild.id
        if not self.isInVoiceChannel(ctx):
            await self.sendEmbed(ctx.channel, "Not In Voice Channel", f'{ctx.author.mention} You must be in a voice channel to use this command.', delete_after=5)
            return
        try:
            channel = ctx.author.voice.channel
            aid = ctx.author.id
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ? AND guildID = ?", (channel.id, guildID,))
            voiceGroup = c.fetchone()
            if voiceGroup is None and not self.isAdmin(ctx):
                await self.sendEmbed(ctx.channel, "Updated Channel Owner", f"{ctx.author.mention} You can't own that channel!", delete_after=5)
            else:
                for data in channel.members:
                    if data.id == voiceGroup[0]:
                        owner = ctx.guild.get_member(voiceGroup[0])
                        await self.sendEmbed(ctx.channel, "Updated Channel Owner", f"{ctx.author.mention} This channel is already owned by {owner.mention}!", delete_after=5)
                        x = True
                if x == False:
                    c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channel.id))
                    textGroup = c.fetchone()
                    if textGroup is not None:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel is not None:
                        c.execute("UPDATE textChannel SET userID = ? WHERE voiceID = ? AND guildID = ?",(aid, channel.id, guildID,))

                    await self.sendEmbed(ctx.channel, "Updated Channel Owner", f"{ctx.author.mention} You are now the owner of the channel!", delete_after=5)
                    c.execute("UPDATE voiceChannel SET userID = ? WHERE voiceID = ? AND guildID = ?", (aid, channel.id, guildID,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()
            await ctx.message.delete()

    @voice.command()
    # @commands.has_role("Admin")
    async def delete(self, ctx):
        if self.isAdmin(ctx):
            guildID = ctx.guild.id
            conn = sqlite3.connect(self.settings.db_path)
            c = conn.cursor()
            c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ?", (guildID, ))
            chans = [item for clist in c.fetchall() for item in clist]
            vchans = [chan for chan in ctx.guild.channels if chan.id in chans]

            embed = discord.Embed(title=f"Delete Voice Channel", description="Choose Which Voice Channel To Delete.", color=0x7289da)
            embed.set_author(name=f"{self.settings.name} v{self.settings.APP_VERSION}", url=self.settings.url,
                            icon_url=self.settings.icon)
            channel_array = []
            index = 0
            for c in vchans:
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
                    chan = self.bot.get_channel(channel_array[selected_index - 1])
                    if chan:
                        print(f"Attempting to remove users in {chan}")
                        for mem in chan.members:
                            await mem.move_to(None, reason="Deleting Channel")
                        await self.sendEmbed(ctx.channel, "Channel Deleted", f'The channel {chan.name} has been deleted.', delete_after=5)
        else:
            print(f"{ctx.author} tried to run command 'delete'")
        await ctx.message.delete()

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
        return ctx.author.voice.channel is not None
    def isAdmin(self, ctx):
        admin_role = discord.utils.find(lambda r: r.name == self.settings.admin_role, ctx.message.guild.roles)
        return admin_role in ctx.author.roles

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


def setup(bot):
    bot.add_cog(voice(bot))
