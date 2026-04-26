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

from shinobu.beacon.models import user as beacon_user

class BeaconModerator:
    """Represents a moderator.
    Moderators can lock Spaces, ban users/servers, etc."""

    def __init__(self, user_id: str, platform: str):
        self._id: str = user_id
        self._platform: str = platform

    @property
    def id(self) -> str:
        return self._id

    @property
    def platform(self) -> str:
        return self._platform

    def to_dict(self):
        return {
            "id": self.id,
            "platform": self.platform
        }

class BeaconAdmin(BeaconModerator):
    """Represents an admin.
    Admins can do everything moderators can and also manage Spaces and moderators."""

class BeaconModManager:
    def __init__(self):
        self._scheme_version: int = 1
        self._moderators: dict[str, BeaconModerator] = {}
        self._admins: dict[str, BeaconAdmin] = {}

    @property
    def moderators(self) -> list[BeaconModerator]:
        return list(self._moderators.values()) + list(self._admins.values())

    @property
    def admins(self) -> list[BeaconAdmin]:
        return list(self._admins.values())

    def add_moderator(self, moderator: BeaconModerator):
        """Adds a Beacon moderator."""
        self._moderators.update({moderator.id: moderator})

    def add_moderators(self, moderators: list[BeaconModerator]):
        """Adds Beacon moderators."""

        for moderator in moderators:
            self.add_moderator(moderator)

    def add_admin(self, admin: BeaconAdmin):
        """Adds a Beacon admin."""
        self._moderators.update({admin.id: admin})

    def add_admins(self, admins: list[BeaconAdmin]):
        """Adds Beacon admins."""

        for admin in admins:
            self.add_admin(admin)

    def is_moderator(self, user: beacon_user.BeaconUser | str):
        if isinstance(user, beacon_user.BeaconUser):
            user = user.id

        return user in self._moderators or user in self._admins

    def is_admin(self, user: beacon_user.BeaconUser | str):
        if isinstance(user, beacon_user.BeaconUser):
            user = user.id

        return user in self._admins

    def remove_moderator(self, mod_id: str):
        self._moderators.pop(mod_id)

    def remove_admin(self, admin_id: str):
        self._admins.pop(admin_id)

    def to_dict(self) -> dict:
        data = {"moderators": {}, "admins": {}}

        for mod, mod_obj in self._moderators.items():
            data["moderators"][mod] = mod_obj.to_dict()

        for admin, admin_obj in self._admins.items():
            data["admins"][admin] = admin_obj.to_dict()

        return data
