import inspect
import math
import os
import re
import traceback
import typing

from bot.cogs.lib import logger, settings, utils
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.mongodb.tracking import TrackingDatabase
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.command(name='changelog', aliases=['changes', "cl"])
    async def changelog(self, ctx):
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            with open(self.settings.changelog, 'r', encoding="UTF-8") as f:
                changelog_data = f.read().strip()

            # split changelog into sections based on '**\d{1,}\.\d{1,}\.\d{1,}**'
            sections = re.split(r'(\*\*v?\d{1,}\.\d{1,}\.\d{1,}\*\*)', changelog_data)
            versions = {}
            cversion = None
            for s in list(filter(lambda x: x != '' and x is not None, sections)):
                if s == '' or s is None:
                    continue

                if s.startswith('**'):
                    cversion = s.strip()
                    versions[cversion] = ''
                else:
                    if cversion and cversion in versions:
                        versions[cversion] += s
            # chunk in to 25 sections
            chunked = utils.chunk_list(list(versions.keys()), 25)
            pages = math.ceil(len(list(versions.keys())) / 25)
            page = 1
            for chunk in chunked:
                fields = list()
                for v in chunk:
                    # get the version from the section
                    if v and v in versions:
                        section = versions[v]
                        s = section
                        if s:
                            # if section is longer than 1024 characters, truncate and add '…'
                            if len(section) > 1024:
                                s = section[:1023] + '…'
                            fields.append({"name": v, "value": s, "inline": False})
                if len(fields) > 0:
                    await self.messaging.send_embed(
                        ctx.channel,
                        self.settings.get_string(
                            guild_id, "help_changelog_title", bot_name=self.settings.name, page=page, total_pages=pages
                        ),
                        "",
                        footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version),
                        fields=fields,
                    )
                page += 1

            self.tracking_db.track_command(
                guildId=guild_id,
                userId=ctx.author.id,
                command="changelog",
                args=None,
            )
        except Exception as ex:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.group(name="help", aliases=["h"], invoke_without_command=True)
    async def help(self, ctx, command: typing.Optional[str] = None, subcommand: typing.Optional[str] = None):
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0
        if guild_id != 0:
            await ctx.message.delete()
        if command is None or command == "":
            await self.root_help(ctx)
            self.tracking_db.track_command(
                guildId=guild_id,
                userId=ctx.author.id,
                command="help",
                args={"type": "command"},
            )
        else:
            await self.subcommand_help(ctx, command, subcommand)
            self.tracking_db.track_command(
                guildId=guild_id,
                userId=ctx.author.id,
                command="help",
                args={"type": "command", "subcommand": subcommand},
            )

    async def subcommand_help(self, ctx, command: typing.Optional[str] = None, subcommand: typing.Optional[str] = None):
        _method = inspect.stack()[1][3]
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0

        try:
            command = command.lower() if command else ""
            subcommand = subcommand.lower() if subcommand else ""

            if command == "" or command is None:
                await self.root_help(ctx)
                return

            command_list: dict = self.settings.get('commands', {})
            if command not in command_list.keys():
                await self.messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "help_info_title", command=command),
                    self.settings.get_string(guild_id, "help_no_command", command=command),
                    color=0xFF0000,
                    delete_after=20,
                )
                return

            cmd = command_list[command]

            fields = list()
            is_admin = False
            if 'admin' in cmd:
                is_admin = cmd['admin']
            shield = '🛡️' if is_admin else ''
            fields.append(
                {
                    "name": f"{shield}{self.settings.get_string(guild_id, cmd['title'])}",
                    "value": self.settings.get_string(guild_id, cmd['description']),
                }
            )
            fields.append({"name": 'help', "value": f"`{self._prefix(guild_id, cmd['usage'])}`"})
            fields.append({
                "name": 'more',
                "value": self._prefix(guild_id, f'`{{{{prefix}}}}help {command.lower()}`'),
            })
            if 'examples' in cmd:
                example_list = [f"`{self._prefix(guild_id, e)}`" for e in cmd['examples']]
                if example_list and len(example_list) > 0:
                    examples = '\n'.join(example_list)
                    fields.append({"name": 'examples', "value": examples})
            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(
                    guild_id, "help_command_title", bot_name=self.settings.name, command=command
                ),
                message="",
                footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version),
                fields=fields,
            )

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
                    fields.append(
                        {
                            "name": f"{shield}{self.settings.get_string(guild_id, scmd['title'])}",
                            "value": self.settings.get_string(guild_id, scmd['description']),
                        }
                    )
                    fields.append({"name": 'help', "value": f"`{self._prefix(guild_id, scmd['usage'])}`"})
                    fields.append(
                        {
                            "name": 'more',
                            "value": self._prefix(guild_id, f'`{{{{prefix}}}}help {command.lower()} {k.lower()}`'),
                        }
                    )
                    if 'examples' in scmd:
                        example_list = [f"`{self._prefix(guild_id, e)}`" for e in scmd['examples']]
                        if example_list and len(example_list) > 0:
                            examples = '\n'.join(example_list)
                            fields.append({"name": 'examples', "value": examples})

                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(
                        guild_id, "help_group_title", bot_name=self.settings.name, page=page, total_pages=pages
                    ),
                    message="",
                    footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version),
                    fields=fields,
                )
                page += 1

        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
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
                    if 'hidden' in cmd and cmd['hidden']:
                        continue
                    is_admin = False
                    if 'admin' in cmd:
                        is_admin = cmd['admin']
                    shield = '🛡️' if is_admin else ''
                    fields.append(
                        {
                            "name": f"{shield}{self.settings.get_string(guild_id, cmd['title'])}",
                            "value": self.settings.get_string(guild_id, cmd['description'])
                        }
                    )
                    fields.append({"name": 'help', "value": f"`{self._prefix(guild_id, cmd['usage'])}`"})
                    fields.append({"name": 'more', "value": self._prefix(guild_id, f'`{{{{prefix}}}}help {k.lower()}`')})
                    if 'examples' in cmd:
                        example_list = [f"`{self._prefix(guild_id, e)}`" for e in cmd['examples']]
                        if example_list and len(example_list) > 0:
                            examples = '\n'.join(example_list)
                            fields.append({"name": 'examples', "value": examples})
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=f"{self.settings.name} Help ({page}/{pages})",
                    message="",
                    footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version),
                    fields=fields,
                )
                page += 1
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    def clean_command_name(self, command):
        return command.replace("_", " ").lower()

    def _prefix(self, guild_id: int, s: str):
        prefix = self.settings.db.get_prefixes(guild_id)[0]
        return utils.str_replace(s, prefix=self.settings.get("prefixes", [prefix])[0])

    @help.command(name="")
    async def help_command(self, ctx):
        pass


async def setup(bot):
    await bot.add_cog(Help(bot))
