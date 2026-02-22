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

from shinobu.beacon.models import space as beacon_space

class BeaconSpaceManager:
    def __init__(self):
        self._spaces: dict[str, beacon_space.BeaconSpace] = {}

    def add_spaces(self, spaces: list[beacon_space.BeaconSpace]):
        for space in spaces:
            if space.id in self._spaces:
                continue

            self._spaces.update({space.id: space})

    def get_space(self, space_id: str) -> beacon_space.BeaconSpace:
        return self._spaces.get(space_id)

    def delete_space(self, space_id: str):
        self._spaces.pop(space_id)

    def to_dict(self) -> dict:
        data = {}
        for space, space_obj in self._spaces.items():
            data[space] = space_obj.to_dict()

        return data
