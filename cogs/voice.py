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
        c.execute(
            "CREATE TABLE IF NOT EXISTS `guildSettings` ( `guildID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER )")
        c.execute(
            "CREATE TABLE IF NOT EXISTS `userSettings` ( `userID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER )")
        c.execute(
            "CREATE TABLE IF NOT EXISTS `voiceChannel` ( `userID` INTEGER, `voiceID` INTEGER )")
        conn.commit()
        c.close()
        conn.close()

    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.environ['VCB_DB_PATH'] or 'voice.db'
        self.admin_ids = os.environ["ADMIN_USERS"].split(" ")
        self.initDB()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        guildID = member.guild.id
        c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
        voice = c.fetchone()
        if voice is None:
            print(f"No voice channel found for GuildID: {guildID}")
            pass
        else:
            voiceID = voice[0]
            try:
                if after.channel.id == voiceID:
                    c.execute(
                        "SELECT * FROM voiceChannel WHERE userID = ?", (member.id,))
                    cooldown = c.fetchone()
                    if cooldown is None:
                        pass
                    else:
                        await member.send("Creating channels too quickly you've been put on a 15 second cooldown!")
                        await asyncio.sleep(15)
                    c.execute(
                        "SELECT voiceCategoryID FROM guild WHERE guildID = ?", (guildID,))
                    voice = c.fetchone()
                    c.execute(
                        "SELECT channelName, channelLimit FROM userSettings WHERE userID = ?", (member.id,))
                    setting = c.fetchone()
                    c.execute(
                        "SELECT channelLimit FROM guildSettings WHERE guildID = ?", (guildID,))
                    guildSetting = c.fetchone()
                    if setting is None:
                        name = f"{member.name}'s channel"
                        if guildSetting is None:
                            limit = 0
                        else:
                            limit = guildSetting[0]
                    else:
                        if guildSetting is None:
                            name = setting[0]
                            limit = setting[1]
                        elif guildSetting is not None and setting[1] == 0:
                            name = setting[0]
                            limit = guildSetting[0]
                        else:
                            name = setting[0]
                            limit = setting[1]
                    categoryID = voice[0]
                    category = self.bot.get_channel(categoryID)
                    print(f"Creating channel {name} in {category}")
                    channel2 = await member.guild.create_voice_channel(name, category=category)
                    channelID = channel2.id
                    print(f"Moving {member} to {channel2}")
                    await member.move_to(channel2)
                    print(f"Setting permissions on {channel2}")
                    await channel2.set_permissions(self.bot.user, connect=True, read_messages=True)
                    print(f"Set user limit to {limit} on {channel2}")
                    await channel2.edit(name=name, user_limit=limit)
                    print(f"Track voiceChannel {id},{channelID}")
                    c.execute(
                        "INSERT INTO voiceChannel VALUES (?, ?)", (id, channelID))
                    conn.commit()

                    def check(a, b, c):
                        return len(channel2.members) == 0
                    await self.bot.wait_for('voice_state_update', check=check)
                    print(f"Deleting Channel {channel2} because everyone left")
                    await channel2.delete()
                    await asyncio.sleep(3)
                    c.execute('DELETE FROM voiceChannel WHERE userID=?', (id,))
            except Exception as ex:
                print(ex)
                pass
        conn.commit()
        conn.close()

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="Help", description="", color=0x7289da)
        embed.set_author(name="Voice Create", url="http://darthminos.tv",
                         icon_url="https://i.imgur.com/EIqP24c.png")
        embed.add_field(name=f'**Commands**', value=f'**Lock your channel by using the following command:**\n\n`.voice lock`\n\n------------\n\n'
                        f'**Unlock your channel by using the following command:**\n\n`.voice unlock`\n\n------------\n\n'
                        f'**Change your channel name by using the following command:**\n\n`.voice name <name>`\n\n**Example:** `.voice name EU 5kd+`\n\n------------\n\n'
                        f'**Change your channel limit by using the following command:**\n\n`.voice limit number`\n\n**Example:** `.voice limit 2`\n\n------------\n\n'
                        f'**Give users permission to join by using the following command:**\n\n`.voice permit @person`\n\n**Example:** `.voice permit @Sam#9452`\n\n------------\n\n'
                        f'**Claim ownership of channel once the owner has left:**\n\n`.voice claim`\n\n**Example:** `.voice claim`\n\n------------\n\n'
                        f'**Remove permission and the user from your channel using the following command:**\n\n`.voice reject @person`\n\n**Example:** `.voice reject @Sam#9452`\n\n', inline='false')
        embed.set_footer(
            text='Bot developed by Sam#9452. Improved by DarthMinos#1161')
        await ctx.channel.send(embed=embed)

    @commands.group()
    async def voice(self, ctx):
        pass

    @voice.command(pass_context=True)
    async def setup(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        guildID = ctx.guild.id
        print(f"User id triggering setup: {ctx.author.id}")
        print(f"Owner id: {ctx.guild.owner.id}")
        print(self.admin_ids)
        print(str(ctx.author.id) in self.admin_ids)
        id = ctx.author.id
        if ctx.author.id == ctx.guild.owner.id or str(ctx.author.id) in self.admin_ids:
            def check(m):
                return m.author.id == ctx.author.id
            await ctx.channel.send("**You have 60 seconds to answer each question!**")
            await ctx.channel.send(f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**")
            try:
                category = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await ctx.channel.send('Took too long to answer!')
            else:
                new_cat = await ctx.guild.create_category_channel(category.content)
                await ctx.channel.send('**Enter the name of the voice channel: (e.g Join To Create)**')
                try:
                    channel = await self.bot.wait_for('message', check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await ctx.channel.send('Took too long to answer!')
                else:
                    try:
                        channel = await ctx.guild.create_voice_channel(channel.content, category=new_cat)
                        c.execute(
                            "SELECT * FROM guild WHERE guildID = ? AND ownerID=?", (guildID, id))
                        voiceGroup = c.fetchone()
                        if voiceGroup is None:
                            c.execute("INSERT INTO guild VALUES (?, ?, ?, ?)",
                                      (guildID, id, channel.id, new_cat.id))
                        else:
                            c.execute("UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?", (
                                guildID, id, channel.id, new_cat.id, guildID))
                        await ctx.channel.send("**You are all setup and ready to go!**")
                    except Exception as e:
                        print(e)
                        await ctx.channel.send("You didn't enter the names properly.\nUse `.voice setup` again!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")
        conn.commit()
        conn.close()

    @commands.command(pass_context=True)
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

    @voice.command()
    async def lock(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        id = ctx.author.id
        print(f"{ctx.author} triggered lock")
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (id,))
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
    async def unlock(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        id = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (id,))
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
        id = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (id,))
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
        id = ctx.author.id
        guildID = ctx.guild.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (id,))
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
        id = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (id,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.edit(user_limit=limit)
            await ctx.channel.send(f'{ctx.author.mention} You have set the channel limit to be ' + '{}!'.format(limit))
            c.execute(
                "SELECT channelName FROM userSettings WHERE userID = ?", (id,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO userSettings VALUES (?, ?, ?)",
                          (id, f'{ctx.author.name}', limit))
            else:
                c.execute(
                    "UPDATE userSettings SET channelLimit = ? WHERE userID = ?", (limit, id))
        conn.commit()
        conn.close()

    @voice.command()
    async def name(self, ctx, *, name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        id = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (id,))
        voiceGroup = c.fetchone()
        if voice is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.edit(name=name)
            await ctx.channel.send(f'{ctx.author.mention} You have changed the channel name to ' + '{}!'.format(name))
            c.execute(
                "SELECT channelName FROM userSettings WHERE userID = ?", (id,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute(
                    "INSERT INTO userSettings VALUES (?, ?, ?)", (id, name, 0))
            else:
                c.execute(
                    "UPDATE userSettings SET channelName = ? WHERE userID = ?", (name, id))
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
            id = ctx.author.id
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
                    c.execute(
                        "UPDATE voiceChannel SET userID = ? WHERE voiceID = ?", (id, channel.id))
            conn.commit()
            conn.close()


def setup(bot):
    bot.add_cog(voice(bot))
