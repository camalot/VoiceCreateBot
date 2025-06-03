import typing

class GuildSettings:
    def __init__(self, guildId: int, prefixes: typing.List[str], defaultRole: int, adminRoles: typing.List[int], language: str):
        self.guild_id = str(guildId)
        self.default_role = str(defaultRole)
        self.admin_roles = [str(r) for r in adminRoles]
        self.prefixes = prefixes
        self.language = language
