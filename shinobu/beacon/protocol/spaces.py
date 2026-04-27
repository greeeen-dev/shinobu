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

from shinobu.beacon.models import space as beacon_space, channel as beacon_channel

class BeaconSpaceIsPrivate(Exception):
    pass

class BeaconSpaceExists(Exception):
    pass

class BeaconSpaceIsNsfw(Exception):
    pass

class BeaconSpaceManager:
    def __init__(self, allow_private_spaces: bool = False):
        self._scheme_version: int = 1
        self._spaces: dict[str, beacon_space.BeaconSpace] = {}
        self._invite_mapping: dict[str, str] = {}
        self._allow_private_spaces: bool = allow_private_spaces

    @property
    def allow_private_spaces(self) -> bool:
        return self._allow_private_spaces

    @property
    def all_spaces(self) -> list[beacon_space.BeaconSpace]:
        return list(self._spaces.values())

    def add_space(self, space: beacon_space.BeaconSpace, creating: bool = False):
        """Adds a Space to Beacon."""

        # Run sanity checks
        if creating:
            if not self.allow_private_spaces and space.private:
                # If Private Spaces are disabled, we should prevent creation
                raise BeaconSpaceIsPrivate("Private Spaces are disabled")
            if space.nsfw:
                # Age gate should be configurable but not enabled on creation
                raise BeaconSpaceIsNsfw("Cannot create a Space with age-gate on by default")

        if space.id in self._spaces:
            if creating:
                raise BeaconSpaceExists(f"Space with id {space.id} already registered")
            return

        self._spaces.update({space.id: space})

        # Add invites to mapping
        for invite in space.invites:
            self._invite_mapping.update({invite.code: space.id})

    def add_spaces(self, spaces: list[beacon_space.BeaconSpace], creating: bool = False):
        """Adds Spaces to Beacon."""

        for space in spaces:
            self.add_space(space, creating=creating)

    def get_space(self, space_id: str) -> beacon_space.BeaconSpace | None:
        return self._spaces.get(space_id)

    def get_space_for_channel(self, channel: beacon_channel.BeaconChannel) -> beacon_space.BeaconSpace | None:
        for space_id in self._spaces:
            space = self._spaces[space_id]
            matches = [member for member in space.partial_members if member.channel_id == channel.id]

            if len(matches) > 0:
                return space

        return None

    def delete_space(self, space_id: str):
        self._spaces.pop(space_id)

    def to_dict(self) -> dict:
        data = {}
        for space, space_obj in self._spaces.items():
            data[space] = space_obj.to_dict()

        return data
