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


class voice(commands.Cog):

    def initDB(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS `guild` ( `guildID` INTEGER, `ownerID` INTEGER, `voiceChannelID` INTEGER, `voiceCategoryID` INTEGER )")
        c.execute("CREATE TABLE IF NOT EXISTS `guildSettings` ( `guildID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER )")
        c.execute("CREATE TABLE IF NOT EXISTS `guildCategorySettings` ( `guildID` INTEGER,  `voiceCategoryID` INTEGER, `channelLimit` INTEGER, `channelLocked` INTEGER )")
        c.execute("CREATE TABLE IF NOT EXISTS `userSettings` ( `guildID` INTEGER, `userID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER )")
        c.execute("CREATE TABLE IF NOT EXISTS `voiceChannel` ( `guildID` INTEGER, `userID` INTEGER, `voiceID` INTEGER )")
        conn.commit()
        c.close()
        conn.close()

    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.environ['VCB_DB_PATH'] or 'voice.db'
        print(f"DB Path: {self.db_path}")
        self.admin_ids = os.environ["ADMIN_USERS"].split(" ")
        self.initDB()

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
                # # get empty channels
                # c.execute("SELECT voiceID from voiceChannel WHERE guildID = ?", (guildID,))
                # known_channels = [item for chans in c.fetchall() for item in chans]
                # chans = [vc.id for vc in member.guild.voice_channels if vc.id in known_channels]
                # for chanID in chans:
                #     print(f"Looking up: {chanID}")
                #     chan = member.guild.get_channel(chanID)
                #     print(f"Checking chan}")
                #     if chan:
                #         def check_empty(a, b, c):
                #             return len(chan.members) == 0
                #         await self.bot.wait_for('voice_state_update', check=check_empty)
                #         print(f"Deleting Channel {chan} because everyone left")
                #         await chan.delete()
                #         await asyncio.sleep(3)


                if after.channel is not None and after.channel.id in voiceChannels:
                    category_id = after.channel.category_id
                    # c.execute("SELECT * FROM voiceChannel WHERE userID = ?", (member.id,))
                    # cooldown = c.fetchone()
                    # if cooldown is None:
                    #     pass
                    # else:
                    #     await asyncio.sleep(15)

                    # c.execute("DELETE FROM voiceChannel WHERE userID = ?", (member.id,))
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
                            locked = guildSetting[1]
                        elif guildSetting is not None and setting[1] == 0:
                            name = setting[0]
                            limit = guildSetting[0]
                            locked = guildSetting[1]
                        else:
                            name = setting[0]
                            limit = setting[1]
                            locked = guildSetting[1]
                    mid = member.id
                    category = self.bot.get_channel(category_id)
                    print(f"Creating channel {name} in {category}")
                    channel2 = await member.guild.create_voice_channel(name, category=category)
                    channelID = channel2.id
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
                    c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildID, mid, channelID,))
                    conn.commit()

                    def check(a, b, c):
                        return len(channel2.members) == 0
                    await self.bot.wait_for('voice_state_update', check=check)
                    print(f"Deleting Channel {channel2} because everyone left")
                    await channel2.delete()
                    await asyncio.sleep(3)
                    c.execute('DELETE FROM voiceChannel WHERE userID = ?', (mid,))
            except Exception as ex:
                print(ex)
                traceback.print_exc()
        conn.commit()
        conn.close()


    @commands.group()
    async def voice(self, ctx):
        pass

    @voice.command()
    async def help(self, ctx, command=""):
        app = {}
        with open('app.manifest') as json_file:
            app = json.load(json_file)
        command_list = app['commands']
        if command and command.lower() in command_list:
            cmd = command_list[command.lower()]
            if cmd['admin'] and self.isAdmin(ctx):
                embed = discord.Embed(title=f"Help '{command.lower()}'", description=cmd['help'], color=0x7289da)
                embed.set_author(name=f"{app['name']} v{app['version']}", url=app['url'],
                                icon_url=app['icon'])
                embed.add_field(name=f'**Usage**', value=cmd['usage'], inline='false')
                embed.add_field(name=f'**Example**', value=cmd['example'], inline='false')
                embed.set_footer(text=f'Developed by {app["author"]}')
                await ctx.channel.send(embed=embed)
        else:
            embed = discord.Embed(title=f"Help Commands", description="List of available help commands", color=0x7289da)
            embed.set_author(name=f"{app['name']} v{app['version']}", url=app['url'],
                            icon_url=app['icon'])
            for k in command_list:
                embed.add_field(name=k, value=f".voice help {k}", inline='false')
            embed.set_footer(text=f'Developed by {app["author"]}')
            await ctx.channel.send(embed=embed)

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
            await ctx.channel.send("**You have 60 seconds to answer each question!**")
            await ctx.channel.send(f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**")
            try:
                category = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await ctx.channel.send('Took too long to answer!')
            else:
                # found_category = await next((x for x in ctx.guild.categories if x.name == category.content), None)
                # if found_category:
                #     # found existing with that name.
                #     # do you want to create a new one?
                #     await ctx.channel.send(f"**Found an existing channel called '{str(found_category)}'. Use that? Reply: YES or NO.**")
                #     try:
                #         yes_or_no = await self.bot.wait_for('message', check=check, timeout=60.0)
                #     except asyncio.TimeoutError:
                #         await ctx.channel.send('Took too long to answer!')
                #     else:
                # else:
                new_cat = await ctx.guild.create_category_channel(category.content)
                await ctx.channel.send('**Enter the name of the voice channel: (e.g Join To Create)**')
                try:
                    channel = await self.bot.wait_for('message', check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await ctx.channel.send('Took too long to answer!')
                else:
                    try:
                        channel = await ctx.guild.create_voice_channel(channel.content, category=new_cat)
                        c.execute("SELECT * FROM guild WHERE guildID = ? AND ownerID=? AND voiceChannelID=?", (guildID, aid, channel.id))
                        voiceGroup = c.fetchone()
                        if voiceGroup is None:
                            c.execute("INSERT INTO guild VALUES (?, ?, ?, ?)", (guildID, aid, channel.id, new_cat.id))
                        else:
                            c.execute("UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?", (
                                guildID, aid, channel.id, new_cat.id, guildID))
                        await ctx.channel.send("**You are all setup and ready to go!**")
                    except Exception as e:
                        traceback.print_exc()
                        await ctx.channel.send("You didn't enter the names properly.\nUse `.voice setup` again!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")
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
            await ctx.send("You have changed the default channel limit for your server!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")
        conn.commit()
        conn.close()

    @setup.error
    async def info_error(self, ctx, error):
        print(error)
        traceback.print_exc()
    @voice.command()
    async def lock(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        print(f"{ctx.author} triggered lock")
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            role = discord.utils.get(ctx.guild.roles, name='@everyone')
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(role, connect=False, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} Voice chat locked! 🔒')
        conn.commit()
        conn.close()

    @voice.command()
    async def settings(self, ctx, category, locked="False", limit="0"):
        if self.isAdmin(ctx):
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            print(f'cat: {category}')
            print(f'locked: {locked}')
            print(f'limit: {limit}')
            found_category = next((x for x in ctx.guild.categories if x.name == category), None)
            if found_category:
                c.execute("SELECT channelLimit, channelLocked FROM guildCategorySettings WHERE guildID = ? AND voiceCategoryID = ?", (ctx.guild.id, found_category.id,))
                catSettings = c.fetchone()
                if catSettings:
                    print(f"UPDATE category settings")
                    c.execute("UPDATE guildCategorySettings SET channelLimit = ?, channelLocked = ? WHERE guildID = ? AND channelLimit = ?",
                        (int(limit), str2bool(locked), ctx.guild.id, found_category.id,))
                else:
                    print(f"INSERT category settings")
                    c.execute("INSERT INTO guildCategorySettings VALUES ( ?, ?, ?, ? )", (ctx.guild.id, found_category.id, int(limit), str2bool(locked),))
            else:
                print(f"No Category found for '{category}'")
            conn.commit()
            conn.close()
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")

    @voice.command()
    async def unlock(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            role = discord.utils.get(ctx.guild.roles, name='@everyone')
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(role, connect=True, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} Voice chat unlocked! 🔓')
        conn.commit()
        conn.close()

    @voice.command(aliases=["allow"])
    async def permit(self, ctx, member: discord.Member):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(member, connect=True)
            await ctx.channel.send(f'{ctx.author.mention} You have permitted {member.name} to have access to the channel. ✅')
        conn.commit()
        conn.close()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx, member: discord.Member):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            for members in channel.members:
                if members.id == member.id:
                    c.execute(
                        "SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
                    voiceGroup = c.fetchone()
                    channel2 = self.bot.get_channel(voiceGroup[0])
                    await member.move_to(channel2)
            await channel.set_permissions(member, connect=False, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} You have rejected {member.name} from accessing the channel. ❌')
        conn.commit()
        conn.close()

    @voice.command()
    async def limit(self, ctx, limit):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.edit(user_limit=limit)
            await ctx.channel.send(f'{ctx.author.mention} You have set the channel limit to be ' + '{}!'.format(limit))
            c.execute(
                "SELECT channelName FROM userSettings WHERE userID = ?", (aid,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO userSettings VALUES (?, ?, ?)",
                          (aid, f'{ctx.author.name}', limit))
            else:
                c.execute(
                    "UPDATE userSettings SET channelLimit = ? WHERE userID = ?", (limit, aid))
        conn.commit()
        conn.close()

    @voice.command()
    async def name(self, ctx, *, name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voice is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            if channel is not None:
                await channel.edit(name=name)
                await ctx.channel.send(f'{ctx.author.mention} You have changed the channel name to {name}!')
                c.execute("SELECT channelName FROM userSettings WHERE userID = ?", (aid,))
                voiceGroup = c.fetchone()
                if voiceGroup is None:
                    c.execute("INSERT INTO userSettings VALUES (?, ?, ?)", (aid, name, 0))
                else:
                    c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ?", (name, aid))
        conn.commit()
        conn.close()

    @voice.command()
    async def claim(self, ctx):
        x = False
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        channel = ctx.author.voice.channel
        if channel == None:
            await ctx.channel.send(f"{ctx.author.mention} you're not in a voice channel.")
        else:
            aid = ctx.author.id
            c.execute(
                "SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel.id,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await ctx.channel.send(f"{ctx.author.mention} You can't own that channel!")
            else:
                for data in channel.members:
                    if data.id == voiceGroup[0]:
                        owner = ctx.guild.get_member(voiceGroup[0])
                        await ctx.channel.send(f"{ctx.author.mention} This channel is already owned by {owner.mention}!")
                        x = True
                if x == False:
                    await ctx.channel.send(f"{ctx.author.mention} You are now the owner of the channel!")
                    c.execute("UPDATE voiceChannel SET userID = ? WHERE voiceID = ?", (aid, channel.id))
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

    def isAdmin(self, ctx):
        return ctx.author.id == ctx.guild.owner.id or str(ctx.author.id) in self.admin_ids

def setup(bot):
    bot.add_cog(voice(bot))

def str2bool(v):
    return v.lower() in ("yes", "true", "yup", "1", "t", "y")
