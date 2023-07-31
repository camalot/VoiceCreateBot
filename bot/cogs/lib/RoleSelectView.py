import discord
from discord.ext import commands
import traceback
import inspect
import os
import typing

from . import settings
from . import logger
from . import loglevel


class RoleSelectView(discord.ui.View):
    def __init__(
        self,
        ctx,
        placeholder: str,
        exclude_roles=None,
        select_callback: typing.Optional[typing.Callable] = None,
        timeout_callback: typing.Optional[typing.Callable] = None,
        allow_none: bool = False,
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.log = logger.Log(minimumLogLevel=log_level)

        self.ctx = ctx
        roles = [r for r in ctx.guild.roles if exclude_roles is None or r.id not in [x.id for x in exclude_roles]]
        roles.sort(key=lambda r: r.position)
        self.role_select = RoleSelect(ctx, placeholder, roles, allow_none)
        self.select_callback = select_callback
        self.timeout_callback = timeout_callback

        self.role_select.callback = self.on_select_callback
        self.add_item(self.role_select)

    async def on_select_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.ctx.author.id:
          return
        await interaction.response.defer()
        if self.select_callback is not None:
            await self.select_callback(self.role_select, interaction)
            self.stop()

    async def on_timeout(self, interaction: discord.Interaction) -> None:
        self.clear_items()
        if self.timeout_callback is not None:
            await self.timeout_callback()


class RoleSelect(discord.ui.Select):
    def __init__(self, ctx, placeholder: str, roles, allow_none: bool = False) -> None:
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
        if len(roles) == 0 or len(roles) >= max_items:
            options.append(
                discord.SelectOption(label=self.settings.get_string(ctx.guild.id, "other"), value="0", emoji="⏭")
            )
            # sub_message = self.get_string(guild_id, 'ask_admin_role_submessage')
        if allow_none:
            options.append(
                discord.SelectOption(label=self.settings.get_string(ctx.guild.id, "none"), value="-1", emoji="⛔")
            )
        for r in roles[:max_items]:
            self.log.debug(ctx.guild.id, f"{self._module}.{_method}", f"Adding role {r.name} to options")
            options.append(discord.SelectOption(label=r.name, value=str(r.id), emoji="🏷"))
        self.options = options
