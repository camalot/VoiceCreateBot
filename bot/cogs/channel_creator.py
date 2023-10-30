import inspect
import os
import traceback

import discord
from bot.cogs.lib import channels, logger, messaging, settings, users, utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.channels import ChannelsDatabase
from bot.cogs.lib.mongodb.usersettings import UserSettingsDatabase
from bot.cogs.lib.mongodb.guilds import GuildsDatabase
from bot.cogs.lib.models.embedfield import EmbedField
from bot.cogs.lib.enums.category_settings_defaults import CategorySettingsDefaults
from discord.ext import commands


class ChannelCreatorCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__

        self.channel_db = ChannelsDatabase()
        self.usersettings_db = UserSettingsDatabase()
        self.guild_db = GuildsDatabase()

        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        self.bot = bot
        self._messaging = messaging.Messaging(bot)
        self._users = users.Users(bot)
        self._channels = channels.Channels(bot)

        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._class}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        _method = inspect.stack()[1][3]
        guild_id = member.guild.id
        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"On Voice State Update")

        voiceChannels = self.guild_db.get_guild_create_channels(guild_id)
        if voiceChannels is None:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"No voice create channels found for GuildID: {guild_id}",
            )
            pass
        else:
            try:
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"Check for user in Create Channel"
                )
                for voiceChannel in voiceChannels:
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Check for user in Create Channel {voiceChannel}",
                    )

                if after.channel is not None and after.channel.id in voiceChannels:
                    # User Joined the CREATE CHANNEL
                    self.log.debug(
                        guild_id, f"{self._module}.{self._class}.{_method}", f"User requested to CREATE CHANNEL"
                    )
                    category_id = after.channel.category_id
                    source_channel = after.channel
                    source_channel_id = after.channel.id
                    channel_owner_id = self.channel_db.get_channel_owner_id(
                        guildId=guild_id, channelId=source_channel_id
                    )
                    if channel_owner_id is None:
                        channel_owner_id = member.id
                        
                    userSettings = self.usersettings_db.get_user_settings(
                        guildId=guild_id, userId=channel_owner_id or member.id
                    )
                    guildSettings = self.settings.db.get_guild_category_settings(
                        guildId=guild_id, categoryId=category_id
                    )
                    useStage = self.guild_db.get_use_stage_on_create(
                        guildId=guild_id, channelId=source_channel_id, categoryId=category_id
                    ) or 0

                    # CHANNEL SETTINGS START
                    limit = CategorySettingsDefaults.CHANNEL_LIMIT_DEFAULT.value
                    locked = False
                    auto_name = True
                    auto_game = False
                    allow_soundboard = False
                    bitrate = CategorySettingsDefaults.BITRATE_DEFAULT.value
                    name = utils.get_random_name()
                    user_name = name
                    # get game activity from all activities
                    game_activity = None
                    for activity in member.activities:
                        if activity.type == discord.ActivityType.playing:
                            game_activity = activity
                            break

                    is_playing = game_activity is not None

                    default_role_id = self.settings.db.get_default_role(
                        guildId=guild_id, categoryId=category_id, userId=member.id
                    )

                    if default_role_id is None:
                        default_role = member.guild.default_role
                    else:
                        default_role = utils.get_by_name_or_id(
                            member.guild.roles, default_role_id
                        ) or member.guild.default_role

                    if userSettings is None:
                        if guildSettings is not None:
                            limit = guildSettings.channel_limit
                            locked = guildSettings.channel_locked
                            bitrate = guildSettings.bitrate
                            auto_name = guildSettings.auto_name
                            auto_game = guildSettings.auto_game
                            allow_soundboard = guildSettings.allow_soundboard
                    else:
                        user_name = userSettings.channel_name
                        if guildSettings is None:
                            limit = userSettings.channel_limit
                            bitrate = userSettings.bitrate
                            locked = userSettings.channel_locked
                            auto_name = userSettings.auto_name
                            auto_game = userSettings.auto_game
                            allow_soundboard = userSettings.allow_soundboard
                        else:
                            limit = userSettings.channel_limit or guildSettings.channel_limit
                            locked = userSettings.channel_locked or guildSettings.channel_locked or False
                            bitrate = userSettings.bitrate or guildSettings.bitrate
                            auto_name = userSettings.auto_name if userSettings is not None else guildSettings.auto_name
                            auto_game = userSettings.auto_game if userSettings is not None else guildSettings.auto_game
                            allow_soundboard = userSettings.allow_soundboard if userSettings is not None else guildSettings.allow_soundboard

                        if not auto_name:
                            if auto_game and is_playing:
                                name = game_activity.name
                            else:
                                name = user_name

                    # CHANNEL SETTINGS END

                    mid = member.id
                    category = discord.utils.get(member.guild.categories, id=category_id)
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Creating channel {name} in {category} with bitrate {bitrate}kbps",
                    )
                    is_community = member.guild.features.count("COMMUNITY") > 0
                    if(useStage and is_community):
                        self.log.debug(
                            guild_id, f"{self._module}.{self._class}.{_method}", f"Creating Stage Channel"
                        )
                        stage_topic = utils.get_random_name(noun_count=1, adjective_count=2)
                        voiceChannel = await member.guild.create_stage_channel(
                            name,
                            topic=stage_topic,
                            category=category,
                            reason="Create Stage Channel Request by {member}",
                            position=0,
                        )
                    else:
                        self.log.debug(
                            guild_id, f"{self._module}.{self._class}.{_method}", f"Created Voice Channel"
                        )
                        voiceChannel = await source_channel.clone(
                            name=name, reason="Create Channel Request by {member}"
                        )

                    textChannel = await member.guild.create_text_channel(name, category=category, position=0)
                    await textChannel.edit(sync_permissions=True)
                    channelID = voiceChannel.id

                    self.log.debug(
                        guild_id, f"{self._module}.{self._class}.{_method}", f"Moving {member} to {voiceChannel}"
                    )
                    await member.move_to(voiceChannel)
                    # if the bot cant do this, dont fail...
                    try:
                        self.log.debug(guild_id, _method , f"Setting permissions on {voiceChannel}")
                        # if use_voice_activity is not True, some cases where people cant speak, unless they use P2T
                        await voiceChannel.set_permissions(
                            member,
                            speak=True,
                            priority_speaker=True,
                            connect=True,
                            read_messages=True,
                            send_messages=True,
                            view_channel=True,
                            use_voice_activation=True,
                            stream=True,
                            move_members=True,
                            use_soundboard=allow_soundboard,
                        )
                        await textChannel.set_permissions(
                            member,
                            read_messages=True,
                            send_messages=True,
                            view_channel=True,
                            read_message_history=True,
                            use_soundboard=allow_soundboard,
                        )
                    except Exception as ex:
                        self.log.error(
                            guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc()
                        )
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Set user limit to {limit} on {voiceChannel}",
                    )
                    await voiceChannel.edit(name=name, user_limit=limit, bitrate=(bitrate*1000), position=0)

                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Track voiceChannel userID: {mid} channelID: {channelID}",
                    )
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Track Voice and Text Channels {name} in {category}",
                    )

                    self.channel_db.track_new_channel_set(
                        guildId=guild_id, ownerId=mid, voiceChannelId=channelID, textChannelId=textChannel.id
                    )

                    try:
                        if default_role:
                            self.log.debug(
                                guild_id,
                                f"{self._module}.{self._class}.{_method}",
                                f"Check if bot can set channel for {default_role.name} {voiceChannel}",
                            )
                            await textChannel.set_permissions(
                                default_role,
                                read_messages=(not locked),
                                send_messages=(not locked),
                                read_message_history=(not locked),
                                view_channel=True,
                            )
                            await voiceChannel.set_permissions(
                                default_role,
                                speak=True,
                                connect=(not locked),
                                read_messages=(not locked),
                                send_messages=(not locked),
                                view_channel=True,
                                stream=(not locked),
                                use_voice_activation=True,
                                move_members=(not locked),
                                use_soundboard=allow_soundboard,
                            )
                    except Exception as ex:
                        self.log.error(
                            guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc()
                        )

                    await self._messaging.send_embed(
                        textChannel,
                        self.settings.get_string(guild_id, 'title_new_voice_text_channel'),
                        f"{member.mention}, {self.settings.get_string(guild_id, 'info_new_voice_text_channel')}",
                        delete_after=None,
                        footer=None,
                    )
                    # init_message contains keys that point to strings in the language file.
                    init_message = self.settings.init_message
                    if init_message:
                        # title, message, fields=None, delete_after=None, footer=None
                        fields = []

                        prefix = self.settings.db.get_prefixes(guild_id)[0]
                        for f in range(len(init_message['fields'])):
                            fields.append(
                                EmbedField(
                                    self.settings.get_string(guild_id, init_message['fields'][f]['name']),
                                    utils.str_replace(init_message['fields'][f]['value'], prefix=prefix),
                                ).to_dict()
                            )
                        await self._messaging.send_embed(
                            textChannel,
                            self.settings.get_string(guild_id, init_message['title']),
                            f"{member.mention}, {self.settings.get_string(guild_id, init_message['message'])}",
                            fields=fields,
                            delete_after=None,
                            footer=None,
                        )
            except discord.errors.NotFound as nf:
                self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", str(nf))
            except Exception as ex:
                self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

async def setup(bot):
    await bot.add_cog(ChannelCreatorCog(bot))
