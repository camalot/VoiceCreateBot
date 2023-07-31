import typing



class GuildSettings:
    def __init__(self, guildId: int, prefix, defaultRole: int, adminRole: int, language: str):
        self.guild_id = guildId
        self.default_role = defaultRole
        self.admin_role = adminRole
        self.prefix = prefix
        self.language = language


class GuildSettingsV2:
    def __init__(self, guildId: int, prefixes: typing.List[str], defaultRole: int, adminRoles: typing.List[int], language: str):
        self.guild_id = guildId
        self.default_role = defaultRole
        self.admin_roles = adminRoles
        self.prefixes = prefixes
        self.language = language

    @staticmethod
    def from_v1(v1: GuildSettings) -> 'GuildSettingsV2':
        return GuildSettingsV2(
            guildId=v1.guild_id,
            prefixes=[v1.prefix],
            defaultRole=v1.default_role,
            adminRoles=[v1.admin_role],
            language=v1.language
        )

    @staticmethod
    def from_v1_dict(d: dict) :
        return GuildSettingsV2(
            guildId=d['guild_id'],
            prefixes=[d['prefix']],
            defaultRole=d['default_role'],
            adminRoles=[d['admin_role']],
            language=d['language']
        )
