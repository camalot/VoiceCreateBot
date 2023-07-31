import discord
from discord.ext import commands
import traceback
import inspect
import os
from . import settings
from . import logger
from . import loglevel


class ChannelSelect(discord.ui.Select):
    def __init__(self, ctx, placeholder: str, channels, allow_none: bool = False) -> None:
        max_items = 24 if not allow_none else 23
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.ctx = ctx

        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.log = logger.Log(minimumLogLevel=log_level)
        options = []

        if len(channels) >= max_items:
            options.append(
                discord.SelectOption(label=self.settings.get_string(ctx.guild.id, "other"), value="0", emoji="⏭")
            )
            # sub_message = self.get_string(guild_id, 'ask_admin_role_submessage')
        if allow_none:
            options.append(
                discord.SelectOption(label=self.settings.get_string(ctx.guild.id, "none"), value="-1", emoji="⛔")
            )
        for c in channels[:max_items]:
            self.log.debug(ctx.guild.id, f"{self._module}.{_method}", f"Adding channel {c.name} to options")
            options.append(discord.SelectOption(label=c.name, value=str(c.id), emoji="🏷"))
        self.options = options


class ChannelSelectView(discord.ui.View):
    def __init__(
            self,
            ctx,
            placeholder: str,
            channels,
            select_callback=None,
            timeout_callback=None,
            allow_none: bool = False,
            timeout: int = 180
        ) -> None:
        super().__init__(timeout=timeout)
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.log = logger.Log(minimumLogLevel=log_level)

        self.ctx = ctx
        self.channel_select = ChannelSelect(ctx, placeholder, channels, allow_none)

        self.select_callback = select_callback
        self.timeout_callback = timeout_callback

        self.channel_select.callback = self.on_select
        self.add_item(self.channel_select)

    async def on_select(self, interaction: discord.Interaction) -> None:
        _method = inspect.stack()[0][3]
        self.log.debug(self.ctx.guild.id, f"{self._module}.{_method}", "Item Selected")
        await interaction.response.defer()
        if self.select_callback is not None:
            await self.select_callback(self.channel_select, interaction)
            self.stop()

    async def on_timeout(self) -> None:
        _method = inspect.stack()[0][3]
        self.log.debug(self.ctx.guild.id, f"{self._module}.{_method}", "Timed out")
        self.clear_items()
        if self.timeout_callback is not None:
            await self.timeout_callback()

    async def on_error(self, error, item, interaction) -> None:
        _method = inspect.stack()[0][3]
        self.clear_items()
        self.log.error(self.ctx.guild.id, f"{self._module}.{_method}", str(error), traceback.format_exc())
