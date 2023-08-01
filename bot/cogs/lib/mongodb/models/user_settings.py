import typing

class UserSettings():
    def __init__(
            self,
            guildId: int,
            userId: int,
            channelName: str,
            channelLimit: int,
            bitrate: int,
            defaultRole: typing.Union[str, int],
            autoGame: bool,
            allowSoundboard: bool = False,
            autoName: bool = True,
        ):
        self.guild_id = str(guildId)
        self.user_id = str(userId)
        self.channel_name = channelName
        self.channel_limit = channelLimit
        self.bitrate = bitrate
        self.default_role = defaultRole
        self.auto_game = autoGame
        self.allow_soundboard = allowSoundboard
        self.auto_name = autoName
        pass
