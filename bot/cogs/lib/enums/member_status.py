from enum import Enum
import discord

class MemberStatus(Enum):
    ONLINE = 1
    OFFLINE = 2
    IDLE = 3
    DND = 4

    UNKNOWN = 9999

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def from_discord (status: discord.Status) -> "MemberStatus":
        if status == discord.Status.online:
            return MemberStatus.ONLINE
        elif status == discord.Status.offline:
            return MemberStatus.OFFLINE
        elif status == discord.Status.idle:
            return MemberStatus.IDLE
        elif status == discord.Status.dnd:
            return MemberStatus.DND
        else:
            return MemberStatus.UNKNOWN

    @staticmethod
    def from_str (status: str) -> "MemberStatus" :
        if status.lower() == "online":
            return MemberStatus.ONLINE
        elif status.lower() == "offline":
            return MemberStatus.OFFLINE
        elif status.lower() == "idle":
            return MemberStatus.IDLE
        elif status.lower() == "dnd":
            return MemberStatus.DND
        else:
            return MemberStatus.UNKNOWN
