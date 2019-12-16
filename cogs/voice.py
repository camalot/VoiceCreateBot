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

class EmbedField():
    def __init__(self, name, value):
        self.name = name
        self.value = value

class voice(commands.Cog):

    def initDB(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS `guild` ( `guildID` INTEGER, `ownerID` INTEGER, `voiceChannelID` INTEGER, `voiceCategoryID` INTEGER )")
        c.execute("CREATE TABLE IF NOT EXISTS `guildSettings` ( `guildID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER, `prefix` TEXT DEFAULT '.' )")
        c.execute("CREATE TABLE IF NOT EXISTS `guildCategorySettings` ( `guildID` INTEGER,  `voiceCategoryID` INTEGER, `channelLimit` INTEGER, `channelLocked` INTEGER )")
        c.execute("CREATE TABLE IF NOT EXISTS `userSettings` ( `guildID` INTEGER, `userID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER )")
        c.execute("CREATE TABLE IF NOT EXISTS `voiceChannel` ( `guildID` INTEGER, `userID` INTEGER, `voiceID` INTEGER )")
        c.execute("CREATE TABLE IF NOT EXISTS `textChannel` ( `guildID` INTEGER, `userID` INTEGER, `channelID` INTEGER, `voiceID` INTEGER )")
        conn.commit()
        c.close()
        conn.close()

    def __init__(self, bot):
        self.settings = {}
        with open('app.manifest') as json_file:
            self.settings = json.load(json_file)

        self.bot = bot
        self.db_path = os.environ['VCB_DB_PATH'] or 'voice.db'
        print(f"DB Path: {self.db_path}")
        self.admin_ids = os.environ["ADMIN_USERS"].split(" ")
        self.initDB()

    # Clean up empty channels
    async def clean_up_channels(self, guild):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            guildID = guild.id
            c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ?", (guildID,))
            voiceChannels = [item for clist in c.fetchall() for item in clist]
            for chanID in voiceChannels:
                chan = guild.get_channel(chanID)
                if chan is not None and len(chan.members) == 0:
                    print(f"Delete orphan voice channel '{chan.name}'")
                    await chan.delete()
                    c.execute("SELECT channelID FROM textChannel WHERE guildID = ? AND voiceID = ?", (guildID, chanID))
                    textGroup = c.fetchone()
                    textChannel = None
                    if textGroup is not None:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel is not None:
                        print(f"Delete orphan text channel '{textChannel.name}'")
                        await textChannel.delete()
                c.execute("DELETE FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildID, chanID, ))
                c.execute("DELETE FROM textChannel WHERE guildID = ? AND voiceID = ?", (guildID, chanID, ))
            conn.commit()
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        guildID = member.guild.id
        c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
        voiceChannels = [item for clist in c.fetchall() for item in clist]
        if voiceChannels is None:
            print(f"No voice channel found for GuildID: {guildID}")
            pass
        else:
            try:
                await self.clean_up_channels(member.guild)

                if after.channel is not None and after.channel.id in voiceChannels:
                    category_id = after.channel.category_id
                    c.execute("SELECT channelName, channelLimit FROM userSettings WHERE userID = ?", (member.id,))
                    setting = c.fetchone()
                    c.execute("SELECT channelLimit, channelLocked FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildID, category_id,))
                    guildSetting = c.fetchone()
                    if setting is None:
                        name = f"{member.name}'s channel"
                        if guildSetting is None:
                            limit = 0
                            locked = False
                        else:
                            limit = guildSetting[0]
                            locked = guildSetting[1]
                    else:
                        if guildSetting is None:
                            name = setting[0]
                            limit = setting[1]
                            locked = False
                        elif guildSetting is not None and setting[1] == 0:
                            name = setting[0]
                            limit = guildSetting[0]
                            locked = guildSetting[1] or False
                        else:
                            name = setting[0]
                            limit = setting[1]
                            locked = guildSetting[1]
                    mid = member.id
                    category = self.bot.get_channel(category_id)
                    print(f"Creating channel {name} in {category}")
                    channel2 = await member.guild.create_voice_channel(name, category=category)
                    textChannel = await member.guild.create_text_channel(name, category=category)
                    channelID = channel2.id
                    print(f"Track Voice and Text Channels {name} in {category}")
                    c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildID, mid, channelID,))
                    c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildID, mid, textChannel.id, channelID,))
                    conn.commit()

                    print(f"Moving {member} to {channel2}")
                    await member.move_to(channel2)
                    print(f"Setting permissions on {channel2}")
                    await channel2.set_permissions(self.bot.user, connect=True, read_messages=True)
                    print(f"Set user limit to {limit} on {channel2}")
                    await channel2.edit(name=name, user_limit=limit)
                    print(f"Track voiceChannel {mid},{channelID}")
                    role = discord.utils.get(member.guild.roles, name='@everyone')
                    channel = self.bot.get_channel(channelID)
                    await channel.set_permissions(role, connect=(not locked), read_messages=True)

                    def check(a, b, c):
                        return len(channel2.members) == 0
                    await self.bot.wait_for('voice_state_update', check=check)
                    print(f"Deleting Channel {channel2} because everyone left")
                    await channel2.delete()
                    await textChannel.delete()
                    await asyncio.sleep(3)
                    c.execute('DELETE FROM voiceChannel WHERE userID = ?', (mid,))
                    c.execute('DELETE FROM textChannel WHERE userID = ?', (mid,))
            except Exception as ex:
                print(ex)
                traceback.print_exc()
        conn.commit()
        conn.close()


    @commands.group()
    async def voice(self, ctx):
        pass

    @voice.command()
    async def track(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        mid = ctx.author.id
        guildID = ctx.author.guild.id

        channel = None
        try:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            if self.isAdmin(ctx):
                if channel is None:
                    await self.sendEmbed(ctx, "Track Channel", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
                else:
                    c.execute("SELECT voiceID FROM voiceChannel WHERE voiceID = ?", (channel.id,))
                    voiceGroup = c.fetchone()
                    if voiceGroup:
                        await self.sendEmbed(ctx, "Track Channel", f"{ctx.author.mention} This channel is already tracked.", delete_after=5)
                    else:
                        c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildID, mid, channel.id,))
                        conn.commit()
                        await self.sendEmbed(ctx, "Track Channel", f"{ctx.author.mention} The channel '{channel.name}' is now tracked.", delete_after=5)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.close()
            await ctx.message.delete()
    @voice.command()
    async def owner(self, ctx, member: discord.Member):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        channel = None
        if ctx.author.voice:
            channel = ctx.author.voice.channel
        if channel is None:
            await self.sendEmbed(ctx, "Set Channel Owner", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
        else:
            aid = ctx.author.id
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel.id,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await self.sendEmbed(ctx, "Set Channel Owner", f"{ctx.author.mention} That channel is not managed by me. I can't help you own that channel.", delete_after=5)
            else:
                if self.isAdmin(ctx) or ctx.author.id == voiceGroup[0]:
                    await self.sendEmbed(ctx, "Channel Owner Updated", f"{ctx.author.mention}, {member.mention} is now the owner of the channel.", delete_after=5)
                    c.execute("UPDATE voiceChannel SET userID = ? WHERE voiceID = ?", (member.id, channel.id))
                else:
                    await self.sendEmbed(ctx, "Set Channel Owner", f"{ctx.author.mention}, You do not have permission to set the owner of the channel. If the owner left, try `claim`.", delete_after=5)
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
                await self.sendEmbed(ctx, "Voice Channel Prefix", f'Command prefix is now "{prefix}".', delete_after=60)

    @voice.command()
    async def help(self, ctx, command=""):
        command_list = self.settings['commands']
        if command and command.lower() in command_list:
            cmd = command_list[command.lower()]
            if not cmd['admin'] or (cmd['admin'] and self.isAdmin(ctx)):
                embed = discord.Embed(title=f"Help '{command.lower()}'", description=cmd['help'], color=0x7289da)
                embed.set_author(name=f"{self.settings['name']} v{self.settings['version']}", url=self.settings['url'],
                                icon_url=self.settings['icon'])
                embed.add_field(name=f'**Usage**', value=cmd['usage'], inline='false')
                embed.add_field(name=f'**Example**', value=cmd['example'], inline='false')
                embed.set_footer(text=f'Developed by {self.settings["author"]}')
                await ctx.channel.send(embed=embed)
        else:
            embed = discord.Embed(title=f"Help Commands", description="List of available help commands", color=0x7289da)
            embed.set_author(name=f"{self.settings['name']} v{self.settings['version']}", url=self.settings['url'],
                            icon_url=self.settings['icon'])
            for k in command_list:
                embed.add_field(name=k, value=f".voice help {k}", inline='false')
            embed.set_footer(text=f'Developed by {self.settings["author"]}')
            await ctx.channel.send(embed=embed)
        await ctx.message.delete()

    async def ask_category(self, ctx):
        if self.isAdmin(ctx):
            def check(m):
                return m.author.id == ctx.author.id
            def check_yes_no(m):
                return str2bool(m.content)
            await self.sendEmbed(ctx, "Voice Channel Setup", f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**", delete_after=60, footer="**You have 60 seconds to answer**")
            try:
                category = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await ctx.channel.send('Took too long to answer!', delete_after=5)
            else:
                found_category = next((x for x in ctx.guild.categories if x.name.lower() == category.content.lower()), None)
                if found_category:
                    # found existing with that name.
                    # do you want to create a new one?
                    yes_or_no = False
                    await self.sendEmbed(ctx, "Voice Channel Setup", f"**Found an existing channel called '{str(found_category.name.upper())}'. Use that channel? Reply: YES or NO.**", delete_after=60, footer="**You have 60 seconds to answer**")
                    try:
                        yes_or_no = await self.bot.wait_for('message', check=check_yes_no, timeout=60.0)
                    except asyncio.TimeoutError:
                        await self.sendEmbed(ctx, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
                    else:
                        if yes_or_no:
                            return found_category
                        else:
                            return await ctx.guild.create_category_channel(category.content)
                else:
                    return await ctx.guild.create_category_channel(category.content)
        else:
            return None

    @voice.command(pass_context=True)
    async def setup(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        guildID = ctx.guild.id
        print(f"User id triggering setup: {ctx.author.id}")
        print(f"Owner id: {ctx.guild.owner.id}")
        print(self.admin_ids)
        print(str(ctx.author.id) in self.admin_ids)
        aid = ctx.author.id
        # If the person is the OWNER or an ADMIN
        if self.isAdmin(ctx):
            def check(m):
                return m.author.id == ctx.author.id
            # Ask them for the category name
            category = await self.ask_category(ctx)
            await self.sendEmbed(ctx, "Voice Channel Setup", '**Enter the name of the voice channel: (e.g Join To Create)**', delete_after=60, footer="**You have 60 seconds to answer**")
            try:
                channel = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await self.sendEmbed(ctx, "Voice Channel Setup", 'Took too long to answer!', delete_after=5)
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
                    await self.sendEmbed(ctx, "Voice Channel Setup", "You didn't enter the names properly.\nUse `.voice setup` again!", delete_after=5)
        else:
            await self.sendEmbed(ctx, "Voice Channel Setup", f"{ctx.author.mention} only the owner or admins of the server can setup the bot!", delete_after=5)
        await ctx.message.delete()
        conn.commit()
        conn.close()

    @voice.command(pass_context=True)
    async def setlimit(self, ctx, num):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # removed the specific user permission and checked for admin status instead.
        if ctx.author.id == ctx.guild.owner.id or ctx.author.id in self.admin_ids:
            c.execute("SELECT * FROM guildSettings WHERE guildID = ?",
                      (ctx.guild.id,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO guildSettings VALUES (?, ?, ?)",
                          (ctx.guild.id, f"{ctx.author.name}'s channel", num))
            else:
                c.execute(
                    "UPDATE guildSettings SET channelLimit = ? WHERE guildID = ?", (num, ctx.guild.id))
            await self.sendEmbed(ctx, "Channel Set Limit", "You have changed the default channel limit for your server!", delete_after=5)
        else:
            await self.sendEmbed(ctx, "Channel Set Limit", f"{ctx.author.mention} only the owner or admins of the server can setup the bot!", delete_after=5)
        await ctx.message.delete()
        conn.commit()
        conn.close()

    @setup.error
    async def info_error(self, ctx, error):
        print(error)
        traceback.print_exc()


    @voice.command()
    async def lock(self, ctx, roles=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        print(f"{ctx.author} triggered lock")
        c.execute(
            "SELECT voiceID FROM voiceChannel WHERE userID = ? and guildID = ?", (aid, ctx.guild.id, ))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await self.sendEmbed(ctx, "Channel Lock", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
        else:
            channelID = voiceGroup[0]
            role = discord.utils.get(ctx.guild.roles, name='@everyone')
            channel = self.bot.get_channel(channelID)


            # c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channelID))
            # textGroup = c.fetchone()
            # textChannel = None
            # if channel is not None:
            #     if textGroup is not None:
            #         textChannel = self.bot.get_channel(textGroup[0])
            #     if textChannel is not None:
            #         await textChannel.set_permissions(role, read_messages=False,send_messages=False)

            await channel.set_permissions(role, connect=False, read_messages=True)
            if roles:

                for r in roles.split(","):
                    rname = "@" + r.replace("@", "").trim()
                    role = discord.utils.get(ctx.guild.roles, name=rname)
                    await channel.set_permissions(role, connect=True, read_messages=True)

            await self.sendEmbed(ctx, "Channel Lock", f'{ctx.author.mention} Voice chat locked! 🔒', delete_after=5)
        await ctx.message.delete()
        conn.commit()
        conn.close()

    @voice.command()
    async def settings(self, ctx, category, locked="False", limit="0"):
        if self.isAdmin(ctx):
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            found_category = next((x for x in ctx.guild.categories if x.name == category), None)
            if found_category:
                c.execute("SELECT channelLimit, channelLocked, channelBitrate FROM guildCategorySettings WHERE guildID = ? AND voiceCategoryID = ?", (ctx.guild.id, found_category.id,))
                catSettings = c.fetchone()
                if catSettings:
                    print(f"UPDATE category settings")
                    c.execute("UPDATE guildCategorySettings SET channelLimit = ?, channelLocked = ? WHERE guildID = ? AND channelLimit = ?",
                        (int(limit), str2bool(locked), ctx.guild.id, found_category.id,))
                else:
                    print(f"INSERT category settings")
                    c.execute("INSERT INTO guildCategorySettings VALUES ( ?, ?, ?, ? )", (ctx.guild.id, found_category.id, int(limit), str2bool(locked)))
                embed_fields = list()
                embed_fields.append({
                    "name": "Locked",
                    "value": str(locked)
                })
                embed_fields.append({
                    "name": "Limit",
                    "value": str(limit)
                })

                await self.sendEmbed(ctx, "Channel Category Settings", f"Category '{category}' settings have been set.", fields=embed_fields, delete_after=5)

            else:
                print(f"No Category found for '{category}'")
            conn.commit()
            conn.close()
        else:
            await self.sendEmbed(ctx, "Channel Category Settings", f"{ctx.author.mention} only the owner or admins of the server can setup the bot!", delete_after=5)
        await ctx.message.delete()

    @voice.command()
    async def unlock(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute(
            "SELECT voiceID FROM voiceChannel WHERE userID = ? and guildID = ?", (aid, ctx.guild.id,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await self.sendEmbed(ctx, "Channel Unlock", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
        else:
            channelID = voiceGroup[0]
            role = discord.utils.get(ctx.guild.roles, name='@everyone')
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(role, connect=True, read_messages=True)
            await self.sendEmbed(ctx, "Channel Unlock", f'{ctx.author.mention} Voice chat unlocked! 🔓', delete_after=5)
        await ctx.message.delete()
        conn.commit()
        conn.close()

    @voice.command(aliases=["allow"])
    async def permit(self, ctx, member: discord.Member = None, role: discord.Role = None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await self.sendEmbed(ctx, "Grant User Access", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)

            if member:
                await channel.set_permissions(member, connect=True)
                await self.sendEmbed(ctx, "Grant User Access", f'{ctx.author.mention} You have permitted {member.name} to have access to the channel. ✅', delete_after=5)
            if role:
                await channel.set_permissions(role, connect=True)
                await self.sendEmbed(ctx, "Grant User Access", f'{ctx.author.mention} You have permitted {role.name} to have access to the channel. ✅', delete_after=5)

        await ctx.message.delete()
        conn.commit()
        conn.close()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx, member: discord.Member = None, role: discord.Role = None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await self.sendEmbed(ctx, "Reject User Access", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            if member:
                for members in channel.members:
                    if members.id == member.id:
                        member.disconnect()
                await channel.set_permissions(member, connect=False, read_messages=True)
                await self.sendEmbed(ctx, "Reject User Access", f'{ctx.author.mention} You have rejected {member.name} from accessing the channel. ❌', delete_after=5)
            if role:
                for members in channel.members:
                    for roles in members.roles:
                        if roles.id == role.id:
                            member.disconnect()
                await channel.set_permissions(member, connect=False, read_messages=True)
                await self.sendEmbed(ctx, "Reject User Access", f'{ctx.author.mention} You have rejected {member.name} from accessing the channel. ❌', delete_after=5)

        await ctx.message.delete()
        conn.commit()
        conn.close()

    @voice.command()
    async def limit(self, ctx, limit):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? AND guildID = ?", (aid, guildID,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await self.sendEmbed(ctx, "Updated Channel Limit", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.edit(user_limit=limit)
            await self.sendEmbed(ctx, "Updated Channel Limit", f'{ctx.author.mention} You have set the channel limit to be ' + '{}!'.format(limit), delete_after=5)
            c.execute(
                "SELECT channelName FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?)",
                          (ctx.guild.id, aid, f'{ctx.author.name}', limit))
            else:
                c.execute(
                    "UPDATE userSettings SET channelLimit = ? WHERE userID = ? AND guildID = ?", (limit, aid, guildID,))
        await ctx.message.delete()
        conn.commit()
        conn.close()

    # @voice.command()
    # async def bitrate(self, ctx, bitrate):
    #     conn = sqlite3.connect(self.db_path)
    #     c = conn.cursor()
    #     guild = ctx.guild
    #     aid = ctx.author.id
    #     bitrate = int(''.join(i for i in bitrate if i.isdigit())) * 1000
    #     c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
    #     voice=c.fetchone()
    #     if voice is None:
    #         await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
    #     else:
    #         if 8000 <= bitrate <= guild.bitrate_limit:
    #             channelID = voice[0]
    #             role = discord.utils.get(ctx.guild.roles, name='@everyone')
    #             channel = self.bot.get_channel(channelID)
    #             await channel.edit(bitrate=bitrate)
    #             bitrate = int(bitrate / 1000)
    #             await ctx.channel.send(f'{ctx.author.mention} Changed bitrate to {bitrate}kbps.')
    #         else:
    #             await ctx.channel.send(f"{ctx.author.mention} You gave an invalid bitrate.")
    #     conn.commit()
    #     conn.close()

    # @voice.command()
    # async def bitrate(self, ctx, bitrate):
    #     conn = sqlite3.connect(self.db_path)
    #     c = conn.cursor()
    #     aid = ctx.author.id
    #     guildID = ctx.guild.id
    #     c.execute(
    #         "SELECT voiceID FROM voiceChannel WHERE userID = ? AND guildID = ?", (aid, guildID,))
    #     voiceGroup = c.fetchone()
    #     if voiceGroup is None:
    #         await self.sendEmbed(ctx, "Updated Channel Bitrate", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
    #     else:
    #         channelID = voiceGroup[0]
    #         channel = self.bot.get_channel(channelID)
    #         await channel.edit(bitrate=bitrate)
    #         br = bitrate
    #         await self.sendEmbed(ctx, "Updated Channel Bitrate", f'{ctx.author.mention} You have set the channel bitrate to be ' + '{}!'.format(bitrate), delete_after=5)
    #         c.execute(
    #             "SELECT channelName FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
    #         voiceGroup = c.fetchone()
    #         if voiceGroup is None:
    #             c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?)",
    #                       (ctx.guild.id, aid, f'{ctx.author.name}', 0, bitrate))
    #         else:
    #             c.execute(
    #                 "UPDATE userSettings SET bitrate = ? WHERE userID = ? AND guildID = ?", (bitrate, aid, guildID,))
    #     await ctx.message.delete()
    #     conn.commit()
    #     conn.close()

    @voice.command()
    async def name(self, ctx, *, name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ? AND guildID = ?", (aid, guildID,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await self.sendEmbed(ctx, "Updated Channel Name", f"{ctx.author.mention} You don't own a channel.", delete_after=5)
        else:
            channelID = voiceGroup[0]
            c.execute("SELECT channelID FROM textChannel WHERE guildID = ? AND voiceID = ?", (guildID, channelID))
            textGroup = c.fetchone()
            textChannel = None
            channel = self.bot.get_channel(channelID)
            if channel is not None:

                if textGroup is not None:
                    textChannel = self.bot.get_channel(textGroup[0])
                if textChannel is not None:
                    await textChannel.edit(name=name)

                await channel.edit(name=name)
                await self.sendEmbed(ctx, "Updated Channel Name", f'You have changed the channel name to {name}!', delete_after=5)
                c.execute("SELECT channelName FROM userSettings WHERE userID = ? AND guildID = ?", (aid, guildID,))
                voiceGroup = c.fetchone()
                if voiceGroup is None:
                    c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?)", (guildID, aid, name, 0))
                else:
                    c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (name, aid, guildID,))

        await ctx.message.delete()
        conn.commit()
        conn.close()

    @voice.command()
    async def whoowns(self, ctx):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            guildID = ctx.guild.id
            channel = ctx.author.voice.channel
            if channel == None:
                await self.sendEmbed(ctx, "Who Owns Channel", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
            else:
                c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ? AND guildID = ?", (channel.id, guildID,))
                voiceGroup = c.fetchone()
                if voiceGroup is not None:
                    owner = ctx.guild.get_member(voiceGroup[0])
                    await self.sendEmbed(ctx, "Who Owns Channel", f"{ctx.author.mention} The channel '{channel.name}' is owned by {owner.mention}!", delete_after=30)
            conn.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            await ctx.message.delete()

    @voice.command()
    async def claim(self, ctx):
        x = False
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        guildID = ctx.guild.id
        channel = ctx.author.voice.channel
        if channel == None:
            await self.sendEmbed(ctx, "Updated Channel Owner", f"{ctx.author.mention} you're not in a voice channel.", delete_after=5)
        else:
            aid = ctx.author.id
            c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ? AND guildID = ?", (channel.id, guildID,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await self.sendEmbed(ctx, "Updated Channel Owner", f"{ctx.author.mention} You can't own that channel!", delete_after=5)
            else:
                for data in channel.members:
                    if data.id == voiceGroup[0]:
                        owner = ctx.guild.get_member(voiceGroup[0])
                        await self.sendEmbed(ctx, "Updated Channel Owner", f"{ctx.author.mention} This channel is already owned by {owner.mention}!", delete_after=5)
                        x = True
                if x == False:
                    c.execute("SELECT channelID FROM textChannel WHERE userID = ? AND guildID = ? AND voiceID = ?", (aid, guildID, channelID))
                    textGroup = c.fetchone()
                    if textGroup is not None:
                        textChannel = self.bot.get_channel(textGroup[0])
                    if textChannel is not None:
                        c.execute("UPDATE textChannel SET userID = ? WHERE voiceID = ? AND guildID = ?",(aid, channel.id, guildID,))

                    await self.sendEmbed(ctx, "Updated Channel Owner", f"{ctx.author.mention} You are now the owner of the channel!", delete_after=5)
                    c.execute("UPDATE voiceChannel SET userID = ? WHERE voiceID = ? AND guildID = ?", (aid, channel.id, guildID,))
            await ctx.message.delete()
            conn.commit()
            conn.close()

    @voice.command()
    async def delete(self, ctx):
        if self.isAdmin(ctx):
            guildID = ctx.guild.id
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID, ))
            chans = [item for clist in c.fetchall() for item in clist]
            vchans = [chan for chan in ctx.guild.channels if chan.id in chans]

            embed = discord.Embed(title=f"Delete Voice Channel", description="Choose Which Voice Channel To Delete.", color=0x7289da)
            embed.set_author(name=f"{self.settings['name']} v{self.settings['version']}", url=self.settings['url'],
                            icon_url=self.settings['icon'])
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
                    return m.content.isnumeric() and idx >= 0 and idx < len(channel_array)
                result_message = await self.bot.wait_for('message', check=check_index, timeout=60.0)
            except asyncio.TimeoutError:
                await self.sendEmbed(ctx, "Timeout", f'You took too long to answer.', delete_after=5)
                await ctx.channel.send('Took too long to answer!', delete_after=5)
            else:
                selected_index = int(result_message.content)
                if selected_index >= 0:
                    chan = self.bot.get_channel(channel_array[selected_index - 1])
                    if chan:
                        await chan.delete()
                        await self.sendEmbed(ctx, "Channel Deleted", f'The channel {chan.name} has been deleted.', delete_after=5)
        else:
            print(f"{ctx.author} tried to run command 'delete'")
        await ctx.message.delete()

    def isAdmin(self, ctx):
        return ctx.author.id == ctx.guild.owner.id or str(ctx.author.id) in self.admin_ids

    async def sendEmbed(self, ctx, title, message, fields=None, delete_after=None, footer=None):
        embed = discord.Embed(title=title, description=message, color=0x7289da)
        embed.set_author(name=f"{self.settings['name']} v{self.settings['version']}", url=self.settings['url'],
                        icon_url=self.settings['icon'])
        if fields is not None:
            for f in fields:
                embed.add_field(name=f.name, value=f.value, inline='false')
        if footer is None:
            embed.set_footer(text=f'Developed by {self.settings["author"]}')
        else:
            embed.set_footer(text=footer)
        await ctx.channel.send(embed=embed, delete_after=delete_after)


def setup(bot):
    bot.add_cog(voice(bot))

def str2bool(v):
    return v.lower() in ("yes", "true", "yup", "1", "t", "y")
