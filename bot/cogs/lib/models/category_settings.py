import typing

from bot.cogs.lib.enums.category_settings_defaults import CategorySettingsDefaults

class GuildCategorySettings:
    def __init__(
        self,
        guildId: int,
        categoryId: int,
        channelLimit: typing.Optional[int] = None,
        channelLocked: typing.Optional[bool] = None,
        bitrate: typing.Optional[int] = None,
        defaultRole: typing.Optional[typing.Union[str, int]] = None,
        autoGame: typing.Optional[bool] = None,
        allowSoundboard: typing.Optional[bool] = None,
        autoName: typing.Optional[bool] = None,
    ):
        self.guild_id = str(guildId)
        self.category_id = str(categoryId)
        self.channel_limit = channelLimit
        self.channel_locked = channelLocked
        self.bitrate = bitrate
        self.default_role = str(defaultRole) if defaultRole else "@everyone",
        self.auto_game = autoGame
        self.allow_soundboard = allowSoundboard
        self.auto_name = autoName

class PartialGuildCategorySettings(GuildCategorySettings):
    def __init__(self, **kwargs):
        if not kwargs.get("guild_id"):
            if not isinstance(kwargs.get("guild_id"), int):
                raise ValueError("guild_id must be an integer")
            raise ValueError("guild_id is required")

        if not kwargs.get("category_id"):
            if not isinstance(kwargs.get("category_id"), int):
                raise ValueError("category_id must be an integer")
            raise ValueError("category_id is required")

        self.guild_id = int(kwargs.get("guild_id", 0))
        self.category_id = int(kwargs.get("category_id", 0))
        # if kwargs has channel_limit and it is not None
        if kwargs.get("channel_limit") is not None:
            # if channel_limit is not a number
            if not isinstance(kwargs.get("channel_limit"), int):
                raise ValueError("channel_limit must be an integer")
            # if channel_limit is less than 0
            if kwargs.get("channel_limit", CategorySettingsDefaults.CHANNEL_LIMIT_DEFAULT.value) < 0:
                raise ValueError("channel_limit must be greater than or equal to 0")
            self.channel_limit = int(kwargs.get("channel_limit", CategorySettingsDefaults.CHANNEL_LIMIT_DEFAULT.value))

        self.channel_locked = kwargs.get("channel_locked", False)
        if kwargs.get("bitrate") is not None:
            if not isinstance(kwargs.get("bitrate"), int):
                raise ValueError("bitrate must be an integer")
            if kwargs.get("bitrate", CategorySettingsDefaults.BITRATE_DEFAULT.value) < 0:
                raise ValueError("bitrate must be greater than or equal to 0")
            self.bitrate = kwargs.get("bitrate")
        if kwargs.get("default_role") is not None:
            if not isinstance(kwargs.get("default_role"), str) and not isinstance(kwargs.get("default_role"), int):
                raise ValueError("default_role must be a string or an integer")
            self.default_role = str(kwargs.get("default_role", "@everyone"))

        self.auto_game = kwargs.get("auto_game", False)
        self.allow_soundboard = kwargs.get("allow_soundboard", False)
        self.auto_name = kwargs.get("auto_name", True)

        super().__init__(
            guildId=self.guild_id,
            categoryId=self.category_id,
            channelLimit=self.channel_limit,
            channelLocked=self.channel_locked,
            bitrate=self.bitrate,
            defaultRole=self.default_role,
            autoGame=self.auto_game,
            allowSoundboard=self.allow_soundboard,
            autoName=self.auto_name,
        )
