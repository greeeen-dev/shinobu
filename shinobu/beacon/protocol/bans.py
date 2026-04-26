"""
Shinobu - Converse from anywhere, anytime.
Copyright (C) 2026-present  Green (@greeeen-dev)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import time
from enum import Enum
from shinobu.beacon.models import user as beacon_user, server as beacon_server

class BeaconBanType(Enum):
    unknown = 0
    user = 1
    server = 2

    def __int__(self):
        return self.value

class BeaconBan:
    """Represents a moderator.
    Moderators can lock Spaces, ban users/servers, etc."""

    def __init__(self, user_id: str, ban_type: BeaconBanType | int, platform: str | None = None,
                 expiry: int | None = None):
        self._id: str = user_id
        self._type: BeaconBanType = ban_type if type(ban_type) is BeaconBanType else BeaconBanType(ban_type)
        self._expiry: int | None = expiry
        self._platform: str | None = platform

    @property
    def id(self) -> str:
        return self._id

    @property
    def type(self) -> BeaconBanType:
        return self._type

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def expiry(self) -> int | None:
        return self._expiry

    @property
    def is_permanent(self) -> bool:
        return self._expiry is None

    @property
    def expired(self) -> bool:
        if self.is_permanent:
            return False

        return time.time() >= self.expiry

    def to_dict(self):
        return {
            "id": self.id,
            "type": int(self.type),
            "platform": self.platform,
            "expiry": self.expiry
        }

class BeaconBanManager:
    def __init__(self):
        self._scheme_version: int = 1
        self._bans: dict[str, BeaconBan] = {}

    @property
    def bans(self) -> list[BeaconBan]:
        return list(self._bans.values())
        return list(self._admins.values())

    def add_ban(self, ban: BeaconBan):
        """Adds a Beacon ban."""
        self._bans.update({ban.id: ban})

    def add_bans(self, bans: list[BeaconBan]):
        """Adds Beacon bans."""

        for ban in bans:
            self.add_ban(ban)

    def ban(self, user_or_server: beacon_user.BeaconUser | beacon_server.BeaconServer | str,
            duration: int | None = None) -> int | None:
        """Bans a user and returns the ban expiry unix time."""

        # Get ban type, platform and ID
        ban_type: BeaconBanType = BeaconBanType.unknown
        ban_platform: str | None = None

        if isinstance(user_or_server, beacon_user.BeaconUser):
            ban_type = BeaconBanType.user
            ban_id: str = user_or_server.id
            ban_platform = user_or_server.platform
        elif isinstance(user_or_server, beacon_server.BeaconServer):
            ban_type = BeaconBanType.server
            ban_id: str = user_or_server.id
            ban_platform = user_or_server.platform
        else:
            ban_id: str = user_or_server

        # Ban user or server
        ban: BeaconBan = BeaconBan(ban_id, ban_type, ban_platform, round(time.time()) + duration)

        if self.is_banned(user_or_server):
            self._bans[ban.id] = ban
        else:
            self._bans.update({ban.id: ban})

        return ban.expiry

    def is_banned(self, user_or_server: beacon_user.BeaconUser | beacon_server.BeaconServer | str):
        if isinstance(user_or_server, beacon_user.BeaconUser) or isinstance(user_or_server, beacon_server.BeaconServer):
            user_or_server = user_or_server.id

        if user_or_server in self._bans:
            ban: BeaconBan = self._bans[user_or_server]
            if ban.expired:
                self.remove_ban(user_or_server)
                return False
            else:
                return True
        else:
            return False

    def remove_ban(self, ban_id: str):
        self._bans.pop(ban_id)

    def to_dict(self) -> dict:
        data = {}

        for ban, ban_obj in self._bans.items():
            data[ban] = ban_obj.to_dict()

        return data
