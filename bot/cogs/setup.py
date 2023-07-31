import discord
from discord.ext import commands
import traceback

from time import gmtime, strftime
import os
import typing
import inspect
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import logger
from .lib import loglevel
from .lib import member_helper
from .lib.messaging import Messaging

class SetupCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        self.bot = bot

        self.db = mongo.MongoDatabase()
        self.messaging = Messaging(bot)

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", f"Logger initialized with level {log_level.name}")
        self.log.debug(0, f"{self._module}.{_method}", f"Initialized {self._module} cog")


    @commands.group(name='setup', aliases=['s'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        pass

    @setup.command(name='init', aliases=['i'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def init(self, ctx):
        _method = inspect.stack()[0][3]
        try:

            pass
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
    async def prefix(self, ctx, *prefixes):
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()

            if len(prefixes) == 0:
                raise commands.BadArgument("No prefixes provided")

            guild_id = ctx.guild.id
            self.db.set_guild_settings_prefixes(ctx.guild.id, prefixes)
            # self.bot.command_prefix = self.get_prefix
            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "title_prefix"),
                message=f'{ctx.author.mention}, {utils.str_replace(self.settings.get_string(guild_id, "info_set_prefix"), prefix=prefixes[0])}',
                delete_after=10)
            # self.db.set_prefixes_for_guild(ctx.guild.id, prefixes)

            # reload / update the bot's prefix cache
            # self.bot.command_prefix = self.db.get_prefixes_for_guild(ctx.guild.id)

            await ctx.send(f"Prefixes set to {', '.join(prefixes)}")
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"Error: {e}")
            traceback.print_exc()

    @role.command(name="user", aliases=['u'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def user(self, ctx, role: typing.Optional[typing.Union[str, discord.Role]] = None):
        _method = inspect.stack()[0][3]
        try:
            guild_id = ctx.guild.id
            author = ctx.author

            await ctx.message.delete()

            if role is None:
                # NO ROLE PASSED IN. Treat this as a get command
                if member_helper.is_in_voice_channel(ctx.author):
                    voice_channel = ctx.author.voice.channel
                    # category_id = ctx.author.voice.channel.category.id
                    self.db.open()
                    user_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel.id)
                    result_role = self.db.get_default_role(guildId=guild_id, categoryId=voice_channel.category.id, userId=user_id)
                    if result_role:
                        role = self.get_by_name_or_id(ctx.guild.roles, result_role)
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_settings'), f"{author.mention}, {utils.str_replace(self.get_string(guild_id, 'info_get_default_role'), role=role.name)}", fields=None, delete_after=30)
                    else:
                        await self.sendEmbed(ctx.channel, self.get_string(guild_id, 'title_voice_channel_settings'), f"{author.mention}, {self.get_string(guild_id, 'info_default_role_not_found')}", fields=None, delete_after=5)
                else:
                    await self.sendEmbed(ctx.channel, self.get_string(guild_id, "title_not_in_channel"), f'{author.mention}, {self.get_string(guild_id, "info_not_in_channel")}', delete_after=5)
                return

            default_role: discord.Role = ctx.guild.default_role

            if isinstance(role, str):
                default_role = discord.utils.get(ctx.guild.roles, name=role)
            elif isinstance(role, discord.Role):
                default_role = role

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
    async def admin(self, ctx, role: typing.Union[str, discord.Role]):
        _method = inspect.stack()[0][3]
        try:
            admin_role: discord.Role = None

            if isinstance(role, str):
                admin_role = discord.utils.get(ctx.guild.roles, name=role)
            elif isinstance(role, discord.Role):
                admin_role = role

            if admin_role is None:
                raise commands.BadArgument(f"Role {admin_role} not found")

            # self.db.set_admin_role_for_guild(ctx.guild.id, admin_role.id)
            ctx.send(f"Admin role set to {admin_role.name}")
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"Error: {e}")
            traceback.print_exc()


async def setup(bot):
    await bot.add_cog(SetupCog(bot))
