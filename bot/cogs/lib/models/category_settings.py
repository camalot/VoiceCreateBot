import typing

from bot.cogs.lib.enums.category_settings_defaults import CategorySettingsDefaults

class GuildCategorySettings:
    def __init__(
        self,
        guildId: int,
        categoryId: int,
        channelLimit: int = CategorySettingsDefaults.CHANNEL_LIMIT_DEFAULT.value,
        channelLocked: bool = False,
        bitrate: typing.Optional[int] = CategorySettingsDefaults.BITRATE_DEFAULT.value,
        defaultRole: typing.Optional[typing.Union[str, int]] = "@everyone",
        autoGame: bool = False,
        allowSoundboard: bool = False,
        autoName: bool = True,
    ):
        self.guild_id = str(guildId)
        self.category_id = str(categoryId)
        self.channel_limit = channelLimit if channelLimit >= 0 else CategorySettingsDefaults.CHANNEL_LIMIT_DEFAULT.value
        self.channel_locked = channelLocked >= 1
        self.bitrate = bitrate if bitrate else CategorySettingsDefaults.BITRATE_DEFAULT.value
        self.default_role = str(defaultRole) if defaultRole else "@everyone",
        self.auto_game = autoGame
        self.allow_soundboard = allowSoundboard
        self.auto_name = autoName
