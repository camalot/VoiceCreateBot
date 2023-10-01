import discord
from discord.ext import commands
import traceback

from time import gmtime, strftime
import os
import typing
import inspect
from bot.cogs.lib import utils
from bot.cogs.lib import mongo
from bot.cogs.lib.logger import Log
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib import member_helper
from bot.cogs.lib.bot_helper import BotHelper
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.enums.addremove import AddRemoveAction
from bot.cogs.lib.RoleSelectView import RoleSelectView
from bot.cogs.lib.settings import Settings
from bot.cogs.lib.CategorySelectView import CategorySelectView

class SetupCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = Settings()
        self.bot = bot

        self.db = mongo.MongoDatabase()
        self.messaging = Messaging(bot)
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
        pass

    @setup.command(name="channel", aliases=['c'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def channel(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()

            pass
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"Error: {e}")
            traceback.print_exc()

    @setup.command(name='init', aliases=['i'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def init(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()


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
                    await self.messaging.send_embed(ctx.channel, self.settings.get_string(guild_id, "title_role_not_found"), f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_role_not_found')}", delete_after=5)
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
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"Error: {e}")
            traceback.print_exc()

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
            await ctx.message.delete()

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

            await ctx.message.delete()

            if inputRole is None:
                # NO ROLE PASSED IN. Treat this as a get command
                if member_helper.is_in_voice_channel(ctx.author):
                    voice_channel = ctx.author.voice.channel
                    self.db.open()
                    user_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel.id)
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
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"Error: {e}")
            traceback.print_exc()

    @role.command(name="admin", aliases=['a'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx, action: typing.Optional[AddRemoveAction],  role: typing.Optional[typing.Union[str, discord.Role]]):
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()
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
            self.log.error(guild_id, f"{self._module}.{_method}", f"Error: {e}")
            traceback.print_exc()


async def setup(bot):
    await bot.add_cog(SetupCog(bot))
