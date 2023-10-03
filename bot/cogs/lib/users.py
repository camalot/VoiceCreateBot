import typing

from bot.cogs.lib import settings, utils

class Users():
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()

    def isInVoiceChannel(self, ctx):
        # if ctx is Member
        if hasattr(ctx, "voice"):
            return ctx.voice and ctx.voice.channel is not None
        # if ctx is Context
        return ctx.author and ctx.author.voice and ctx.author.voice.channel is not None

    def isAdmin(self, ctx):
        guild_settings = self.settings.get(ctx.guild.id)
        is_in_guild_admin_role = False
        # see if there are guild settings for admin role
        if guild_settings:
            guild_admin_role = utils.get_by_name_or_id(ctx.guild.roles, guild_settings.admin_role)
            is_in_guild_admin_role = guild_admin_role in ctx.author.roles
        is_bot_owner = str(ctx.author.id) == self.settings.bot_owner
        has_admin = ctx.author.guild_permissions.administrator or ctx.author.permission_in(ctx.channel).manage_guild
        return is_bot_owner or is_in_guild_admin_role or has_admin

    async def get_or_fetch_user(self, userId: typing.Optional[int]):
        try:
            if userId is not None:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except Exception as ex:
            return None

    async def get_or_fetch_member(self, guild, userId: typing.Optional[int]):
        try:
            if userId:
                user = guild.get_member(userId)
                if not user:
                    user = await guild.fetch_member(userId)
                return user
            return None
        except Exception as ex:
            return None
