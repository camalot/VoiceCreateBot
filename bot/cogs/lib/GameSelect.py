import discord
from discord.ext import commands
import typing
import traceback
import inspect
import os
from . import settings
from . import logger
from bot.cogs.lib.enums.loglevel import LogLevel


class GameSelect(discord.ui.Select):
    def __init__(self, ctx, placeholder: str, member: discord.Member, allow_none: bool = False) -> None:
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

        if member.activities is None:
            self.options = options
            return

        guild_id = ctx.guild.id

        game_activity = [a for a in member.activities if a.type == discord.ActivityType.playing]
        stream_activity: typing.List[discord.Streaming] = [a for a in member.activities if a.type == discord.ActivityType.streaming]
        watch_activity = [a for a in member.activities if a.type == discord.ActivityType.watching]

        games = []

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

        if len(games) >= max_items:
            options.append(
                discord.SelectOption(label=self.settings.get_string(guild_id, "other"), value="0", emoji="⏭")
            )
            # sub_message = self.get_string(guild_id, 'ask_admin_role_submessage')
        if allow_none:
            options.append(
                discord.SelectOption(label=self.settings.get_string(guild_id, "none"), value="-1", emoji="⛔")
            )
        for c in games[:max_items]:
            self.log.debug(guild_id, f"{self._module}.{_method}", f"Adding game {c.name} to options")
            options.append(discord.SelectOption(label=c, value=str(c), emoji="🏷"))

        self.options = options

class GameSelectView(discord.ui.View):
    def __init__(
            self,
            ctx,
            placeholder: str,
            member: discord.Member,
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
        self.game_select = GameSelect(ctx, placeholder, member, allow_none)

        self.select_callback = select_callback
        self.timeout_callback = timeout_callback

        self.game_select.callback = self.on_select
        self.add_item(self.game_select)

    async def on_select(self, interaction: discord.Interaction) -> None:
        _method = inspect.stack()[0][3]
        self.log.debug(self.ctx.guild.id, f"{self._module}.{_method}", "Item Selected")
        # await interaction.response.defer()
        if self.select_callback is not None:
            await self.select_callback(self, interaction)
            self.stop()

    async def on_timeout(self) -> None:
        _method = inspect.stack()[0][3]
        self.log.debug(self.ctx.guild.id, f"{self._module}.{_method}", "Timed out")
        self.clear_items()
        if self.timeout_callback is not None:
            await self.timeout_callback(self)

    async def on_error(self, error, item, interaction) -> None:
        _method = inspect.stack()[0][3]
        self.clear_items()
        self.log.error(self.ctx.guild.id, f"{self._module}.{_method}", str(error), traceback.format_exc())
