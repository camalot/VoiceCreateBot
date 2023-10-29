import discord
from discord.ext import commands
import os
import typing

from bot.cogs.lib.ChannelSelect import ChannelSelect, ChannelSelectView
from bot.cogs.lib.RoleSelectView import RoleSelectView, RoleSelect

import asyncio

from bot.cogs.lib import utils
from bot.cogs.lib import logger
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib import settings
from bot.cogs.lib.models.text_with_attachments import TextWithAttachments
from bot.cogs.lib.YesOrNoView import YesOrNoView


import inspect


class Messaging():
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = settings.Settings()
        self.bot = bot

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

    async def send_embed(
        self,
        channel: typing.Union[
            discord.abc.GuildChannel,
            discord.TextChannel,
            discord.DMChannel,
            discord.GroupChannel,
            discord.Thread,
            discord.User,
            discord.Member,
            discord.abc.Messageable
        ],
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



    async def ask_yes_no(
        self,
        ctx,
        targetChannel: typing.Optional[discord.abc.Messageable] = None,
        question: typing.Optional[str] = "Yes or No?",
        title: typing.Optional[str] = "Yes or No?",
        timeout: typing.Optional[int] = 60,
        fields: typing.Optional[typing.List[dict[str, typing.Any]]]=None,
        thumbnail: typing.Optional[str] = None,
        image: typing.Optional[str] = None,
        content: typing.Optional[str] = None,
        result_callback: typing.Optional[typing.Callable] = None,
        required_user: typing.Optional[typing.Union[discord.User, discord.Member]] = None,
    ):
        channel = targetChannel if targetChannel else ctx.channel if ctx.channel else ctx.author

        async def answer_callback(caller: YesOrNoView, interaction: discord.Interaction):
            # this requires a specific user to perform the interaction
            if required_user and interaction.user != required_user:
                return

            if interaction is None or interaction.data is None:
                if result_callback:
                    await result_callback(False)

            result_id = interaction.data["custom_id"] if interaction.data["custom_id"] else "false"
            result = utils.str2bool(result_id)
            if result_callback:
                await result_callback(result)

        async def timeout_callback(caller: YesOrNoView, interaction: discord.Interaction):
            await self.send_embed(
                channel=channel,
                title=title,
                message=self.settings.get_string(ctx.guild.id, "took_too_long"),
                delete_after=5,
            )
            if result_callback:
                await result_callback(False)

        yes_no_view = YesOrNoView(
            ctx, answer_callback=answer_callback, timeout=timeout or 60, timeout_callback=timeout_callback
        )
        await self.send_embed(
            channel,
            title,
            question,
            view=yes_no_view,
            delete_after=timeout,
            thumbnail=thumbnail,
            image=image,
            fields=fields,
            content=content,
            footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
        )
        return

    async def ask_number(
        self,
        ctx,
        title: str = "Enter Number",
        message: str = "Please enter a number.",
        min_value: int = 0,
        max_value: int = 100,
        timeout: int = 60,
        required_user: typing.Optional[typing.Union[discord.User, discord.Member]] = None,
    ) -> typing.Optional[int]:
        _method = inspect.stack()[1][3]

        def check_user(m):
            same = m.author.id == required_user.id if required_user else True
            return same

        def check_range(m):
            if check_user(m):
                if m.content.isnumeric():
                    val = int(m.content)
                    return val >= min_value and val <= max_value
                return False

        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        channel = ctx.channel if ctx.channel else ctx.author

        number_ask = await self.send_embed(
            channel,
            title,
            f"{message}",
            delete_after=timeout,
            footer=self.settings.get_string(guild_id, "footer_XX_seconds", seconds=timeout),
        )
        try:
            numberResp = await self.bot.wait_for("message", check=check_range, timeout=timeout)
        except asyncio.TimeoutError:
            await self.send_embed(
                ctx.channel, title, self.settings.get_string(guild_id, "took_too_long"), delete_after=5
            )
            return None
        else:
            numberValue = int(numberResp.content)
            try:
                await numberResp.delete()
            except discord.NotFound as e:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Tried to clean up, but the messages were not found.",
                )
            except discord.Forbidden as f:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Tried to clean up, but the bot does not have permissions to delete messages.",
                )
            try:
                await number_ask.delete()
            except discord.NotFound as e:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Tried to clean up, but the messages were not found.",
                )
            except discord.Forbidden as f:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Tried to clean up, but the bot does not have permissions to delete messages.",
                )
        return numberValue

    async def ask_role_list(
        self,
        ctx,
        title: str = "Choose Role",
        message: str = "Please choose a role.",
        exclude_roles: typing.Optional[list] = None,
        timeout: int = 60,
        select_callback: typing.Optional[typing.Callable] = None,
        required_user: typing.Optional[typing.Union[discord.User, discord.Member]] = None,
    ) -> typing.Union[discord.Role, None]:
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id

        async def role_select_callback(select: RoleSelect, interaction: discord.Interaction):
            if required_user and interaction.user != required_user:
                return

            await interaction.delete_original_response()
            if select_callback:
                if select.values:
                    role_id = 0
                    if len(select.values) > 1:
                        role_id = select.values[0]

                    if role_id == 0:
                        await self.send_embed(
                            ctx.channel, title, f"{ctx.author.mention}, ENTER ROLE NAME", delete_after=5
                        )
                        # need to ask for role name
                        await select_callback(None)
                        return
                        # chan_id = await self.ask_channel_by_name_or_id(ctx, title)

                    selected_role: discord.Role = discord.utils.get(ctx.guild.roles, id=str(select.values[0]))

                    if selected_role:
                        self.log.debug(
                            guild_id,
                            f"{self._module}.{self._class}.{_method}",
                            f"{ctx.author.mention} selected the role '{selected_role.name}'",
                        )
                        await select_callback(selected_role)
                        return
                    else:
                        await self.send_embed(
                            ctx.channel, title, f"{ctx.author.mention}, Unknown Role.", delete_after=5
                        )
                        await select_callback(None)
                        return
                else:
                    await select_callback(None)

        async def timeout_callback(select: RoleSelect, interaction: discord.Interaction):
            await interaction.delete_original_response()
            await self.send_embed(
                ctx.channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5
            )

        role_view = RoleSelectView(
            ctx=ctx,
            placeholder=title,
            exclude_roles=exclude_roles,
            select_callback=role_select_callback,
            timeout_callback=timeout_callback,
            timeout=timeout,
        )

        await self.send_embed(
            ctx.channel,
            title,
            message,
            delete_after=timeout,
            footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
            view=role_view,
        )
