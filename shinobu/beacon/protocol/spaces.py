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

class BeaconSpaceManager:
    def __init__(self):
        self._spaces: dict[str, beacon_space.BeaconSpace] = {}

    def add_space(self, space: beacon_space.BeaconSpace):
        if space.id in self._spaces:
            return

        self._spaces.update({space.id: space})

    def add_spaces(self, spaces: list[beacon_space.BeaconSpace]):
        for space in spaces:
            self.add_space(space)

    def get_space(self, space_id: str) -> beacon_space.BeaconSpace | None:
        return self._spaces.get(space_id)

    def get_space_for_channel(self, channel: beacon_channel.BeaconChannel) -> beacon_space.BeaconSpace | None:
        for space_id in self._spaces:
            space = self._spaces[space_id]
            matches = [member for member in space.members if member.channel_id == channel.id]

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
