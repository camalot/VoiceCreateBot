import typing


class GuildCategorySettings:
    def __init__(
        self,
        guildId: int,
        categoryId: int,
        channelLimit: int,
        channelLocked: bool,
        bitrate: int,
        defaultRole: typing.Union[str, int]
    ):
        self.guild_id = str(guildId)
        self.category_id = str(categoryId)
        self.channel_limit = channelLimit
        self.channel_locked = channelLocked >= 1
        self.bitrate = bitrate
        self.default_role = str(defaultRole)
