import discord
import math
import asyncio
import json
import datetime
from discord.ext import commands
import traceback
from urllib.parse import quote
from discord.ext.commands.core import guild_only
import validators
from discord.ext.commands.cooldowns import BucketType

from discord.ext.commands import has_permissions, CheckFailure
from time import gmtime, strftime
import os
import glob
import typing
import inspect
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import logger
from bot.cogs.lib.enums.loglevel import LogLevel

class HelpCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        self.bot = bot

        self.db = mongo.MongoDatabase()

        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", f"Logger initialized with level {log_level.name}")
        self.log.debug(0, f"{self._module}.{_method}", f"Initialized {self._module} cog")


    @commands.group(name="help", aliases=["h"], invoke_without_command=True)
    async def help(self, ctx, command: str = "", subcommand: str = ""):
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0
        if guild_id != 0:
            await ctx.message.delete()
        if command is None:
            await self.root_help(ctx)
        else:
            await self.subcommand_help(ctx, command, subcommand)

    async def subcommand_help(self, ctx, command: str = "", subcommand: str = ""):
        _method = inspect.stack()[1][3]
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0

        try:
            command = command.lower() if command else ""
            subcommand = subcommand.lower() if subcommand else ""

            command_list: dict = self.settings.get('commands', {})
            if command not in command_list.keys():
                await self.messaging.send_embed(ctx.channel,
                    self.settings.get_string(guild_id, "help_title", bot_name=self.settings.get("name", "TacoBot")),
                    self.settings.get_string(guild_id, "help_no_command", command=command),
                    color=0xFF0000, delete_after=20)
                return

            cmd = command_list[command]

            fields = list()
            is_admin = False
            if 'admin' in cmd:
                is_admin = cmd['admin']
            shield = '🛡️' if is_admin else ''
            fields.append({"name": f"{shield}{cmd['title']}", "value": cmd['description']})
            fields.append({"name": 'help', "value": f"`{self._prefix(cmd['usage'])}`"})
            fields.append({"name": 'more', "value": self._prefix(f'`{{{{prefix}}}} help {command.lower()}`')})
            if 'examples' in cmd:
                example_list = [ f"`{self._prefix(e)}`" for e in cmd['examples'] ]
                if example_list and len(example_list) > 0:
                    examples = '\n'.join(example_list)
                    fields.append({"name": 'examples', "value": examples})
            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "help_command_title", bot_name=self.settings.name, command=command),
                message="",
                footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version), fields=fields)


            subcommands = cmd["subcommands"]
            if subcommand is None:
                filtered_list = subcommands.keys()
            else:
                filtered_list = [i for i in subcommands.keys() if i.lower() == subcommand]

            chunked = utils.chunk_list(list(filtered_list), 10)
            pages = math.ceil(len(filtered_list) / 10)
            page = 1
            for chunk in chunked:
                fields = list()
                for k in chunk:
                    scmd = subcommands[k.lower()]
                    is_admin = False
                    if 'admin' in scmd:
                        is_admin = scmd['admin']
                    shield = '🛡️' if is_admin else ''
                    fields.append({"name": f"{shield}{scmd['title']}", "value": scmd['description']})
                    fields.append({"name": 'help', "value": f"`{self._prefix(scmd['usage'])}`"})
                    fields.append({"name": 'more', "value": self._prefix(f'`{{{{prefix}}}} help {command.lower()} {k.lower()}`')})
                    if 'examples' in scmd:
                        example_list = [ f"`{self._prefix(e)}`" for e in scmd['examples'] ]
                        if example_list and len(example_list) > 0:
                            examples = '\n'.join(example_list)
                            fields.append({"name": 'examples', "value": examples})

                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "help_group_title", bot_name=self.settings.name, page=page, total_pages=pages),
                    message="",
                    footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version),
                    fields=fields,)
                page += 1


        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{_method}" , str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def root_help(self, ctx):
        _method = inspect.stack()[1][3]
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0

        try:
            command_list = self.settings.commands
            filtered_list = list()
            filtered_list = [i for i in command_list.keys()]

            chunked = utils.chunk_list(list(filtered_list), 10)
            pages = math.ceil(len(filtered_list) / 10)
            page = 1
            for chunk in chunked:
                fields = list()
                for k in chunk:
                    cmd = command_list[k.lower()]
                    is_admin = False
                    if 'admin' in cmd:
                        is_admin = cmd['admin']
                    shield = '🛡️' if is_admin else ''
                    fields.append({"name": f"{shield}{cmd['title']}", "value": cmd['description']})
                    fields.append({"name": 'help', "value": f"`{self._prefix(cmd['usage'])}`"})
                    fields.append({"name": 'more', "value": self._prefix(f'`{{{{prefix}}}} help {k.lower()}`')})
                    if 'examples' in cmd:
                        example_list = [ f"`{self._prefix(e)}`" for e in cmd['examples'] ]
                        if example_list and len(example_list) > 0:
                            examples = '\n'.join(example_list)
                            fields.append({"name": 'examples', "value": examples})
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=f"{self.settings.name} Help ({page}/{pages})",
                    message="",
                    footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version),
                    fields=fields,)
                page += 1
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{_method}" , str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    def clean_command_name(self, command):
        return command.replace("_", " ").lower()

    def _prefix(self, s):
        return utils.str_replace(s, prefix=self.settings.get("prefixes", [".voice "])[0])
async def setup(bot):
    await bot.add_cog(HelpCog(bot))
