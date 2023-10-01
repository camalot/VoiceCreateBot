import async_timeout
import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import collections

from .ChannelSelect import ChannelSelect, ChannelSelectView
from .RoleSelectView import RoleSelectView, RoleSelect

from discord.ext.commands.cooldowns import BucketType
from discord import (
    SelectOption,
    ActionRow,
    SelectMenu,
)
from discord.ui import Button, Select, TextInput
from discord.ext.commands import has_permissions, CheckFailure

from . import utils
from . import logger
from bot.cogs.lib.enums import loglevel
from . import settings
from . import mongo
from .models import TextWithAttachments
from .YesOrNoView import YesOrNoView


import inspect


class Messaging():
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        self.bot = bot
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

    async def send_embed(
        self,
        channel: typing.Union[discord.abc.GuildChannel, discord.TextChannel, discord.DMChannel, discord.GroupChannel, discord.Thread, discord.User, discord.Member, discord.abc.Messageable],
        title: typing.Optional[str] = None,
        message: typing.Optional[str] = None,
        fields: typing.Optional[list[dict[str, typing.Any]]] = None,
        delete_after: typing.Optional[float] = None,
        footer: typing.Optional[typing.Any] = None,
        view: typing.Optional[discord.ui.View] = None,
        color: typing.Optional[int] = 0x7289DA,
        author: typing.Optional[typing.Union[discord.User, discord.Member]] = None,
        thumbnail: typing.Optional[str] = None,
        image: typing.Optional[str] = None,
        url: typing.Optional[str] = "",
        content: typing.Optional[str] = None,
        files: typing.Optional[list] = None,
    ) -> discord.Message:
        if color is None:
            color = 0x7289DA

        guild_id = 0
        if hasattr(channel, "guild") and channel.guild:
            guild_id = channel.guild.id

        embed = discord.Embed(title=title, description=message, color=color, url=url)
        if author:
            embed.set_author(name=f"{utils.get_user_display_name(author)}", icon_url=author.avatar.url if author.avatar else None)
        if embed.fields is not None:
            for f in embed.fields:
                embed.add_field(name=f.name, value=f.value, inline=f.inline)
        if fields is not None:
            for f in fields:
                embed.add_field(name=f["name"], value=f["value"], inline=f["inline"] if "inline" in f else False)
        if footer is None:
            embed.set_footer(
                text=self.settings.get_string(
                    guild_id,
                    "developed_by",
                    user=self.settings.get("author", "Unknown"),
                    bot_name=self.settings.get("name", "Unknown"),
                    version=self.settings.get("version", "Unknown"),
                )
            )
        else:
            embed.set_footer(text=footer)

        if thumbnail is not None:
            embed.set_thumbnail(url=thumbnail)
        if image is not None:
            embed.set_image(url=image)
        return await channel.send(
            content=content,
            embed=embed,
            delete_after=delete_after,
            view=view,
            files=files
        )

    async def update_embed(
        self,
        message: typing.Optional[discord.Message] = None,
        title: typing.Optional[str] = None,
        description: typing.Optional[str] = None,
        description_append: typing.Optional[bool] = True,
        fields: typing.Optional[list[dict[str, typing.Any]]] = None,
        content: typing.Optional[str] = None,
        footer: typing.Optional[typing.Any] = None,
        view: typing.Optional[discord.ui.View] = None,
        color: typing.Optional[int] = 0x7289DA,
        author: typing.Optional[typing.Union[discord.User, discord.Member]] = None,
    ):
        if not message or len(message.embeds) == 0:
            return
        if color is None:
            color = 0x7289DA
        guild_id = 0
        if message.guild:
            guild_id = message.guild.id
        embed = message.embeds[0]
        if title is None:
            title = embed.title if embed.title is not None else ""
        if description is not None:
            if description_append:
                edescription = ""
                if embed.description is not None and embed.description != "":
                    edescription = embed.description

                description = edescription + "\n\n" + description
            else:
                description = description
        else:
            if embed.description is not None and embed.description != "":
                description = embed.description
            else:
                description = ""
        updated_embed = discord.Embed(color=color, title=embed.title, description=f"{description}", view=view)
        for f in embed.fields:
            updated_embed.add_field(name=f.name, value=f.value, inline=f.inline)
        if fields is not None:
            for f in fields:
                updated_embed.add_field(
                    name=f["name"], value=f["value"], inline=f["inline"] if "inline" in f else False
                )
        if footer is None:
            updated_embed.set_footer(
                text=self.settings.get_string(
                    guild_id,
                    "developed_by",
                    user=self.settings.get("author", "Unknown"),
                    bot_name=self.settings.get("name", "Unknown"),
                    version=self.settings.get("version", "Unknown"),
                )
            )
        else:
            updated_embed.set_footer(text=footer)

        target_content = message.content
        if content:
            target_content = content

        if author:
            updated_embed.set_author(name=f"{utils.get_user_display_name(author)}", icon_url=author.avatar.url if author.avatar else None)

        await message.edit(content=target_content, embed=updated_embed)


    async def notify_of_error(self, ctx):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
        await self.send_embed(
            channel=ctx.channel,
            title=self.settings.get_string(guild_id, "error"),
            message=self.settings.get_string(guild_id, "error_ocurred", user=ctx.author.mention),
            delete_after=30,
        )
