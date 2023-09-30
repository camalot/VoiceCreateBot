import discord
from discord.ext import commands
import traceback
import os
import inspect
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import logger
from .lib import loglevel
from .lib.channels import Channels
from .lib.messaging import Messaging
from .lib.bot_helper import BotHelper
from .lib.GameSelect import GameSelectView

class GameNameCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.channel_helper = Channels(bot)
        self.messaging_helper = Messaging(bot)
        self.bot_helper = BotHelper(bot)

        self.db = mongo.MongoDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", f"Logger initialized with level {log_level.name}")
        self.log.debug(0, f"{self._module}.{_method}", f"Initialized {self._module} cog")

    @commands.group(name="game", aliases=["g"], invoke_without_command=True)
    @commands.guild_only()
    async def game(self, ctx):
        _method = inspect.stack()[0][3]
        await ctx.message.delete()
        pass

    @game.command(name="auto", aliases=["a"])
    @commands.guild_only()
    async def auto(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.messaging_helper.notify_of_error(ctx)

    @game.command(name="name", aliases=["n"])
    @commands.guild_only()
    async def name(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.messaging_helper.notify_of_error(ctx)




    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        _method = inspect.stack()[1][3]
        guild_id = after.guild.id
        try:
            if not after:
                return
            is_in_channel = after is not None and after.voice is not None and after.voice.channel is not None
            if is_in_channel:
                self.db.open()
                self.log.debug(guild_id, _method , f"Member Update Start of user: '{after.name}'")
                voice_channel = after.voice.channel
                voice_channel_id = voice_channel.id
                owner_id = self.db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
                if owner_id is None:
                    # user is in a channel, but not a channel we are tracking
                    self.log.debug(guild_id, _method , f"User:{str(after.id)} is in a channel, but not a channel we are tracking.")
                    return
                if owner_id != after.id:
                    # user is in a channel, but not their channel
                    self.log.debug(guild_id, _method , f"User:{str(after.id)} is in a channel, but not their own channel.")
                    return
                if before.activity == after.activity:
                    # we are only looking at activity
                    self.log.debug(guild_id, _method , f"Before / After activity is the same")
                    return

                owner = await self.bot_helper.get_or_fetch_member(after.guild, owner_id)
                user_settings = self.db.get_user_settings(guild_id, after.id)

                if user_settings and user_settings.auto_game:
                    text_channel_id = self.db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
                    text_channel = None
                    if text_channel_id:
                        text_channel = await self.channel_helper.get_or_fetch_channel(int(text_channel_id))
                    self.log.debug(guild_id, _method , f"trigger auto game change")
                    selected_title = voice_channel.name
                    if owner and text_channel:
                        ctx = {
                            "guild" : after.guild,
                            "author" : owner,
                            "channel" : text_channel
                        }

                        async def timeout_callback(view: discord.ui.View):
                            view.stop()
                            view.clear_items()
                            await ask_message.delete()
                            pass

                        async def select_callback(view: discord.ui.View, interaction: discord.Interaction):
                            view.stop()
                            await ask_message.delete()

                            if interaction is None or interaction.data is None:
                                return
                            if voice_channel is None:
                                return
                            if text_channel is None:
                                return

                            selected_value = interaction.data.get("value", None)
                            if voice_channel.name != selected_value:
                                if text_channel:
                                    self.log.debug(guild_id, _method , f"Change Text Channel Name: {selected_value}")
                                    await text_channel.edit(name=selected_value)
                                    await self.messaging_helper.send_embed(
                                        channel=text_channel,
                                        title=self.settings.get_string(guild_id, 'title_update_channel_name'),
                                        message=f'{utils.str_replace(self.settings.get_string(guild_id, "info_channel_name_change"), name=selected_value)}',
                                        content=f"{after.mention}",
                                        delete_after=5
                                    )
                                await voice_channel.edit(name=selected_value)

                        game_view = GameSelectView(
                            ctx=ctx,
                            placeholder=self.settings.get_string(guild_id, 'title_update_to_game'),
                            member=owner,
                            select_callback=select_callback,
                            timeout_callback=timeout_callback,
                            allow_none=False,
                            timeout=60
                        )

                        ask_message = await self.messaging_helper.send_embed(
                            channel=text_channel,
                            title=self.settings.get_string(guild_id, 'title_update_to_game'),
                            message=f'{utils.str_replace(self.settings.get_string(guild_id, "info_update_to_game"), name=selected_title)}',
                            content=f"{after.mention}",
                            view=game_view
                        )
                    else:
                        self.log.debug(guild_id, _method , f"owner is none, or text_channel is none. Can't ask to choose game.")
                        game_activity = [a for a in after.activities if a.type == discord.ActivityType.playing]
                        stream_activity = [a for a in after.activities if a.type == discord.ActivityType.streaming]
                        watch_activity = [a for a in after.activities if a.type == discord.ActivityType.watching]
                        if game_activity:
                            selected_title = game_activity[0].name
                        elif stream_activity:
                            selected_title = stream_activity[0].game
                        elif watch_activity:
                            selected_title = watch_activity[0].name

                        if selected_title:
                            if voice_channel.name != selected_title:
                                if text_channel:
                                    self.log.debug(guild_id, _method , f"Change Text Channel Name: {selected_title}")
                                    await text_channel.edit(name=selected_title)
                                self.log.debug(guild_id, _method , f"Change Voice Channel Name: {selected_title}")
                                await voice_channel.edit(name=selected_title)
                else:
                    self.log.debug(guild_id, _method , f"trigger name change, but setting is false.")
        except discord.errors.NotFound as nf:
            self.log.warn(guild_id, _method, str(nf), traceback.format_exc())
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
        finally:
            self.db.close()


async def setup(bot):
    await bot.add_cog(GameNameCog(bot))
