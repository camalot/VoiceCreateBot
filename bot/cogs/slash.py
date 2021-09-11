import discord
from discord import guild
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
from .lib import utils
from .lib import settings
from .lib import logger
from .lib import loglevel
from .lib import dbprovider
from discord.ext import commands
from discord_slash import cog_ext, SlashContext, ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
from discord import Embed
class Slash(commands.Cog):
    slash = None
    def __init__(self, bot):
        self.bot = bot
        # slash = self.bot.slash
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "slash.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "slash.__init__", f"SQLITE DB Path: {self.settings.db_path}")
        self.log.debug(0, "slash.__init__", f"Logger initialized with level {log_level.name}")

    def cog_unload(self):
        self.bot.slash.remove_cog_commands(self)

    @commands.Cog.listener()
    async def on_slash_command(self, ctx: SlashContext):
        pass

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: SlashContext, ex):
        pass
    async def on_component_callback(self, ctx: ComponentContext, callback):
        self.log.debug(ctx.guild.id, "on_component_callback", )
        pass
    @cog_ext.cog_slash(name="test", guild_ids=[592430260713422863])
    # @slash.slash(name="test", guild_ids=[592430260713422863])
    async def _test(self, ctx: SlashContext):
        embed = Embed(title="Embed Test")
        buttons = [
            create_button(style=ButtonStyle.green, label="A green button"),
            create_button(style=ButtonStyle.blue, label="A blue button")
        ]
        action_row = create_actionrow(*buttons)
        await ctx.send("Choose Wisely", components=[action_row])
        button_ctx: ComponentContext = await wait_for_component(self.bot, components=action_row)
        # await ctx.send(embed=embed, components=[action_row])
        await ctx.send(content=f"You selected {button_ctx.selected_options}")

    @commands.group()
    async def voice2(self, ctx):
        pass
    @voice2.command(alias="test2")
    async def _test2(self, ctx):
        select = create_select(
            options=[
                create_select_option("Lab Coat", value="coat", emoji="🥼"),
                create_select_option("Test Tube", value="tube", emoji="🧪"),
                create_select_option("Petri Dish", value="dish", emoji="🧫")
            ],
            placeholder="Choose your option",
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )
        action_row = create_actionrow(select)
        ask_context = await ctx.send("Choose Wisely", components=[action_row])
        button_ctx: ComponentContext = await wait_for_component(self.bot, components=action_row)
        await button_ctx.edit_origin(content=f"You selected {button_ctx.selected_options}")

        await ctx.message.delete()
        return True
def setup(bot):
    bot.add_cog(Slash(bot))
