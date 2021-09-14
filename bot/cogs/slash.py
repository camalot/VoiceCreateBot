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
    @commands.group()
    async def voice2(self, ctx):
        pass
    
    @voice2.command(alias="test")
    # @cog_ext.cog_slash(name="test", guild_ids=[592430260713422863])
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


    @voice2.command(alias="test2")
    async def _test2(self, ctx):
        options = []
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and not r.managed and not r.is_integration()]
        roles.sort(key=lambda r: r.name)
        # idx = 0
        sub_message = ""
        if len(roles) >= 24:
            self.log.warn(ctx.guild.id, "ask_default_role", f"Guild has more than 24 roles. Total Roles: {str(len(roles))}")
            options.append(create_select_option(label="->OTHER<-", value="0", emoji="⛔"))
            sub_message = "\n\nOnly 24 Roles Can Be Listed.\nIf Role Not Listed, Choose `->OTHER<-`"
        for r in roles[:24]:
            options.append(create_select_option(label=r.name, value=str(r.id), emoji="🏷"))

        select = create_select(
            options=options,
            placeholder="Choose Default Role",
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )

        action_row = create_actionrow(select)
        ask_context = await ctx.send(f"**Choose Default Role**{sub_message}", components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send('Took too long to answer!', delete_after=5)
        else:
            role_id = int(button_ctx.selected_options[0])
            if role_id == 0:
                # ask for role name or ID
                role_id = discord.utils.get(ctx.guild.roles, name="@everyone").id

            selected_role = discord.utils.get(ctx.guild.roles, id=role_id)
            if selected_role:
                await ctx.send(content=f"You selected `@{selected_role.name}`")
        finally:
            await ask_context.delete()
            await ctx.message.delete()


    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        if isinstance(nameOrId, str):
            return discord.utils.get(iterable, name=str(nameOrId))
        elif isinstance(nameOrId, int):
            return discord.utils.get(iterable, id=int(nameOrId))
        else:
            return None
def setup(bot):
    bot.add_cog(Slash(bot))
