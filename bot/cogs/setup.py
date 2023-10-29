import discord
from discord.ext import commands
import traceback

from time import gmtime, strftime
import os
import typing
import inspect
from bot.cogs.lib import utils
from bot.cogs.lib.logger import Log
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib import member_helper
from bot.cogs.lib.bot_helper import BotHelper
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.enums.addremove import AddRemoveAction
from bot.cogs.lib.mongodb.channels import ChannelsDatabase
from bot.cogs.lib.RoleSelectView import RoleSelectView
from bot.cogs.lib.users import Users
from bot.cogs.lib.settings import Settings
from bot.cogs.lib.CategorySelectView import CategorySelectView
from bot.cogs.lib.models.category_settings import GuildCategorySettings
from bot.cogs.lib.models.category_settings import PartialGuildCategorySettings

class SetupCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = Settings()
        self.bot = bot

        self.channel_db = ChannelsDatabase()

        self.messaging = Messaging(bot)
        self._users = Users(bot)
        self.bot_helper = BotHelper(bot)

        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Logger initialized with level {log_level.name}")
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._class}")


    @commands.group(name='setup', aliases=['s'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx) -> None:
        await ctx.message.delete()
        pass

    @setup.command(name="channel", aliases=['c'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def channel(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        try:
            pass
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.guild_only()
    # @commands.has_permissions(administrator=True)
    async def bitrate(
        self,
        ctx,
        category: typing.Optional[typing.Union[str, discord.CategoryChannel, int]] = None,
        bitrate: typing.Optional[int] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id

        try:
            if not self._users.isAdmin(ctx):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} is not an admin")
                return

            discord_category = None
            if category is None:
                # TODO: ask for the category
                # get the category for the current channel
                discord_category = ctx.channel.category

            if isinstance(category, str):
                discord_category = discord.utils.get(ctx.guild.categories, name=category)
            elif isinstance(category, int):
                discord_category = discord.utils.get(ctx.guild.categories, id=category)

            if discord_category is None:
                raise commands.BadArgument(f"Category {category} not found")

            bitrate_min = 8
            bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))
            bitrate_value = bitrate
            if bitrate_value is None or bitrate_value < bitrate_min or bitrate_value > bitrate_limit:
                bitrate_value = await self.messaging.ask_number(
                    ctx=ctx,
                    title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
                    message=utils.str_replace(
                        self.settings.get_string(guild_id, "info_bitrate"),
                        bitrate_min=str(bitrate_min),
                        bitrate_limit=str(bitrate_limit)
                    ),
                    min_value=8,
                    max_value=bitrate_limit,
                    timeout=60,
                    required_user=ctx.author,
                )

                if bitrate_value is None:
                    bitrate_value = bitrate_limit

            self.settings.db.set_guild_category_settings(
                PartialGuildCategorySettings(
                    guildId=guild_id,
                    categoryId=discord_category.id,
                    bitrate=bitrate_value
                )
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.guild_only()
    async def limit(
        self,
        ctx,
        category: typing.Optional[typing.Union[str, discord.CategoryChannel, int]] = None,
        limit: typing.Optional[int] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id

        try:
            if not self._users.isAdmin(ctx):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} is not an admin")
                return

            discord_category = None
            if category is None:
                # TODO: ask for the category
                # get the category for the current channel
                discord_category = ctx.channel.category

            if isinstance(category, str):
                discord_category = discord.utils.get(ctx.guild.categories, name=category)
            elif isinstance(category, int):
                discord_category = discord.utils.get(ctx.guild.categories, id=category)

            if discord_category is None:
                raise commands.BadArgument(f"Category {category} not found")

            limit_min = 0
            limit_max = 100
            limit_value = limit
            if limit_value is None or limit_value < limit_min or limit_value > limit_max:
                limit_value = await self.messaging.ask_number(
                    ctx=ctx,
                    title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
                    message=self.settings.get_string(guild_id, 'ask_limit'),
                    min_value=limit_min,
                    max_value=limit_max,
                    timeout=60,
                    required_user=ctx.author,
                )

                if limit_value is None:
                    limit_value = 0

            self.settings.db.set_guild_category_settings(
                PartialGuildCategorySettings(
                    guildId=guild_id,
                    categoryId=discord_category.id,
                    limit=limit_value
                )
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.guild_only()
    async def locked(
        self,
        ctx,
        category: typing.Optional[typing.Union[str, discord.CategoryChannel, int]] = None,
        locked: typing.Optional[bool] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id

        try:
            if not self._users.isAdmin(ctx):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} is not an admin")
                return

            discord_category = None
            if category is None:
                # TODO: ask for the category
                # get the category for the current channel
                discord_category = ctx.channel.category

            if isinstance(category, str):
                discord_category = discord.utils.get(ctx.guild.categories, name=category)
            elif isinstance(category, int):
                discord_category = discord.utils.get(ctx.guild.categories, id=category)

            if discord_category is None:
                raise commands.BadArgument(f"Category {category} not found")

            locked_value = locked
            if locked_value is None:
                locked_value = await self.messaging.ask_yes_no(
                    ctx=ctx,
                    title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
                    question=self.settings.get_string(guild_id, 'ask_default_locked'),
                    timeout=60,
                    required_user=ctx.author,
                )

                if locked_value is None:
                    locked_value = False

            self.settings.db.set_guild_category_settings(
                PartialGuildCategorySettings(
                    guildId=guild_id,
                    categoryId=discord_category.id,
                    locked=locked_value
                )
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.guild_only()
    async def default_role(
        self,
        ctx,
        category: typing.Optional[typing.Union[str, discord.CategoryChannel, int]] = None,
        default_role: typing.Optional[typing.Union[str, discord.Role, int]] = None,
    ) -> None:
        pass

    # @setup.command(name="category", aliases=['cat'])
    # @commands.guild_only()
    # async def category(self, ctx):
    #     _method = inspect.stack()[1][3]
    #     guild_id = ctx.guild.id
    #     author = ctx.author

    #     new_default_role = None
    #     locked = False
    #     limit = 0
    #     bitrate_value = 0

    #     try:
    #         if self._users.isAdmin(ctx):
    #             found_category = await self.set_role_ask_category(ctx)
    #             bitrate_min = 8
    #             bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))
    #             if found_category:
    #                 bitrate_value = await self.messaging.ask_number(
    #                     ctx=ctx,
    #                     title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
    #                     message=utils.str_replace(
    #                         self.settings.get_string(guild_id, "info_bitrate"),
    #                         bitrate_min=str(bitrate_min),
    #                         bitrate_limit=str(bitrate_limit)
    #                     ),
    #                     min_value=8,
    #                     max_value=bitrate_limit,
    #                     timeout=60,
    #                     required_user=ctx.author,
    #                 )

    #                 def default_role_callback(result):
    #                     new_default_role = result
    #                     if not new_default_role:
    #                         new_default_role = ctx.guild.default_role

    #                 def locked_yes_no_callback(result):
    #                     locked = result

    #                     limit = self.messaging.ask_number(
    #                         ctx=ctx,
    #                         title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
    #                         message=self.settings.get_string(guild_id, 'ask_limit'),
    #                         min_value=0,
    #                         max_value=99,
    #                         timeout=60,
    #                         required_user=ctx.author,
    #                     )

    #                     ask_role = self.messaging.ask_role_list(
    #                         ctx=ctx,
    #                         title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
    #                         message=self.settings.get_string(guild_id, 'ask_default_role'),
    #                         timeout=60,
    #                         required_user=ctx.author,
    #                         select_callback=default_role_callback,
    #                     )

    #                 ask_locked = await self.messaging.ask_yes_no(
    #                     ctx=ctx,
    #                     targetChannel=ctx.channel,
    #                     question=self.settings.get_string(guild_id, 'ask_default_locked'),
    #                     title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
    #                     timeout=60,
    #                     required_user=ctx.author,
    #                     result_callback=locked_yes_no_callback
    #                 )

    #                 self.settings.db.set_guild_category_settings(
    #                     GuildCategorySettings(
    #                         guildId=guild_id,
    #                         categoryId=found_category.id,
    #                         channelLimit=limit,
    #                         channelLocked=locked,
    #                         autoGame=False,
    #                         allowSoundboard=False,
    #                         autoName=True,
    #                         bitrate=bitrate_value,
    #                         defaultRole=new_default_role.id,
    #                     )
    #                 )
    #                 embed_fields = list([
    #                     {
    #                         "name": self.settings.get_string(guild_id, 'category'),
    #                         "value": found_category.name,
    #                     },
    #                     {
    #                         "name": self.settings.get_string(guild_id, 'locked'),
    #                         "value": str(locked)
    #                     },
    #                     {
    #                         "name": self.settings.get_string(guild_id, 'limit'),
    #                         "value": str(limit)
    #                     },
    #                     {
    #                         "name": self.settings.get_string(guild_id, 'bitrate'),
    #                         "value": f"{str(bitrate_value)}kbps"
    #                     },
    #                     {
    #                         "name": self.settings.get_string(guild_id, 'default_role'),
    #                         "value": f"{new_default_role.name}"
    #                     }
    #                 ])

    #                 await self.messaging.send_embed(
    #                     ctx.channel,
    #                     self.settings.get_string(guild_id, "title_voice_channel_settings"),
    #                     f"""{author.mention}, {
    #                         utils.str_replace(self.settings.get_string(guild_id, 'info_category_settings'), category=found_category.name)
    #                     }""",
    #                     fields=embed_fields,
    #                     delete_after=5,
    #                 )

    #             else:
    #                 self.log.error(guild_id, _method, f"No Category found for '{found_category}'")
    #         else:
    #             await self.messaging.send_embed(
    #                 ctx.channel,
    #                 self.settings.get_string(guild_id, "title_voice_channel_settings"),
    #                 f"{author.mention}, {self.settings.get_string(guild_id, 'setup_no_permission')}",
    #                 delete_after=5,
    #             )
    #     except Exception as ex:
    #         self.log.error(guild_id, _method, str(ex), traceback.format_exc())
    #         await self.messaging.notify_of_error(ctx)

    @setup.command(name='init', aliases=['i'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def init(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            # this should be configurable
            exclude_roles = [r.id for r in ctx.guild.roles if r.name.lower().startswith('lfg-')]
            async def rsv_callback(view, interaction):
                await interaction.response.defer()
                await rsv_message.delete()
                # get the role
                role_id = int(interaction.data['values'][0])
                # get the role object
                role = utils.get_by_name_or_id(ctx.guild.roles, role_id)
                if role is None:
                    await self.messaging.send_embed(
                        ctx.channel,
                        self.settings.get_string(guild_id, "title_role_not_found"),
                        f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_role_not_found')}",
                        delete_after=5,
                    )
                    return

                await ctx.send(f"Role selected: {role.name}")
                selected_role = role

                async def csv_callback(view, interaction):
                    await interaction.response.defer()
                    await csv_message.delete()

                    category_id = int(interaction.data['values'][0])
                    if category_id == -2:
                        # create a new category
                        await ctx.send("TODO: Create a new category", delete_after=5)
                        return
                    if category_id == -1:
                        # no category selected
                        await ctx.send("TODO: No category selected", delete_after=5)
                        return
                    if category_id == 0:
                        # other category selected
                        await ctx.send("TODO: Other category selected", delete_after=5)
                        return

                    # get the role object
                    category: discord.CategoryChannel = utils.get_by_name_or_id(ctx.guild.categories, category_id)
                    if not category:
                        await ctx.send("Category not found", delete_after=5)
                    selected_category = category
                    await ctx.send(f"Category selected: {category.name}")


                async def csv_timeout_callback(view):
                    await csv_message.delete()
                    # took too long to respond
                    await self.messaging.send_embed(ctx.channel, self.settings.get_string(guild_id, "title_timeout"), f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'took_too_long')}", delete_after=5)
                    pass


                csv = CategorySelectView(
                    ctx=ctx,
                    placeholder=self.settings.get_string(guild_id, "title_select_category"),
                    categories=ctx.guild.categories,
                    select_callback=csv_callback,
                    timeout_callback=csv_timeout_callback,
                    allow_none=False,
                    allow_new=True,
                    timeout=60
                )
                csv_message = await ctx.send(view=csv)
            async def rsv_timeout_callback(view):
                await rsv_message.delete()
                # took too long to respond
                await self.messaging.send_embed(ctx.channel, self.settings.get_string(guild_id, "title_timeout"), f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'took_too_long')}", delete_after=5)
                pass


            selected_role = None
            selected_category = None
            # ask for the default user role.
            rsv = RoleSelectView(
                ctx=ctx,
                placeholder=self.settings.get_string(guild_id, "title_select_default_role"),
                exclude_roles=exclude_roles,
                select_callback=rsv_callback,
                timeout_callback=rsv_timeout_callback,
                allow_none=False,

                timeout=60
            )
            rsv_message = await ctx.send(view=rsv)
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    @setup.group(name="role", aliases=['r'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def role(self, ctx):
        pass

    # set prefix command that allows multiple prefixes to be passed in
    @setup.command(name='prefix', aliases=['p'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx, *, prefixes: typing.List[str] = []):
        _method = inspect.stack()[0][3]
        try:
            guild_id = ctx.guild.id
            if len(prefixes) == 0:
                prefixes = self.settings.db.get_prefixes(guildId=guild_id)
                if prefixes is None:
                    await ctx.send_embed(
                        channel=ctx.channel,
                        title="Prefixes",
                        message=f"Prefixes are not set", delete_after=10)
                    return
                await ctx.send_embed(
                    channel=ctx.channel,
                    title="Prefixes",
                    message=f"Prefixes are `{', '.join(prefixes)}`",
                    delete_after=10)
            else:
                self.settings.db.set_prefixes(
                    guildId=ctx.guild.id,
                    prefixes=prefixes
                )
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "title_prefix"),
                    message=f'{ctx.author.mention}, {utils.str_replace(self.settings.get_string(guild_id, "info_set_prefix"), prefix=prefixes[0])}',
                    delete_after=10)

                await ctx.send_embed(
                    channel=ctx.channel,
                    title="Prefixes",
                    message=f"Prefixes set to `{', '.join(prefixes)}`",
                    delete_after=10)
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"Error: {e}")
            traceback.print_exc()

    @role.command(name="user", aliases=['u'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def user(self, ctx, inputRole: typing.Optional[typing.Union[str, discord.Role]] = None):
        _method = inspect.stack()[0][3]
        try:
            guild_id = ctx.guild.id
            author = ctx.author
            if inputRole is None:
                # NO ROLE PASSED IN. Treat this as a get command
                if member_helper.is_in_voice_channel(ctx.author):
                    voice_channel = ctx.author.voice.channel
                    user_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel.id)
                    result_role_id = self.settings.db.get_default_role(
                        guildId=guild_id,
                        categoryId=voice_channel.category.id,
                        userId=user_id
                    )
                    if result_role_id:
                        role: discord.Role = utils.get_by_name_or_id(ctx.guild.roles, result_role_id)
                        await self.messaging.send_embed(
                            channel=ctx.channel,
                            title=self.settings.get_string(guild_id, 'title_voice_channel_settings'),
                            message=f"{author.mention}, {utils.str_replace(self.settings.get_string(guild_id, 'info_get_default_role'), role=role.name)}",
                            fields=None,
                            delete_after=30
                        )
                    else:
                        await self.messaging.send_embed(
                            channel=ctx.channel,
                            title=self.settings.get_string(guild_id, 'title_voice_channel_settings'),
                            message=f"{author.mention}, {self.settings.get_string(guild_id, 'info_default_role_not_found')}",
                            fields=None, delete_after=5
                        )
                else:
                    await self.messaging.send_embed(
                        channel=ctx.channel,
                        title=self.settings.get_string(guild_id, "title_not_in_channel"),
                        message=f'{author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                        delete_after=5
                    )
                return
            default_role: discord.Role = ctx.guild.default_role

            if isinstance(inputRole, str):
                default_role = discord.utils.get(ctx.guild.roles, name=inputRole)
            elif isinstance(inputRole, discord.Role):
                default_role = inputRole

            if default_role is None:
                raise commands.BadArgument(f"Role {default_role} not found")
            # self.db.set_default_role_for_guild(ctx.guild.id, default_role.id)
            ctx.send(f"Default role set to {default_role.name}")
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    @role.command(name="admin", aliases=['a'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx, action: typing.Optional[AddRemoveAction],  role: typing.Optional[typing.Union[str, discord.Role]]):
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            if action is None and role is None:
                # return the list of admin roles
                pass

            admin_role: typing.Optional[discord.Role] = None
            if isinstance(role, str):
                admin_role = discord.utils.get(ctx.guild.roles, name=role)
            elif isinstance(role, discord.Role):
                admin_role = role

            if admin_role is None:
                raise commands.BadArgument(f"Role {admin_role} not found")

            if action == AddRemoveAction.ADD:
                self.settings.db.add_admin_role(guildId=guild_id, roleId=admin_role.id)
                ctx.send(f"Added role {admin_role.name}", delete_after=5)
            elif action == AddRemoveAction.REMOVE:
                self.settings.db.delete_admin_role(guildId=guild_id, roleId=admin_role.id)
                ctx.send(f"Removed role {admin_role.name}", delete_after=5)
        except Exception as e:
            await self.messaging.notify_of_error(ctx)
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())


async def setup(bot):
    await bot.add_cog(SetupCog(bot))
