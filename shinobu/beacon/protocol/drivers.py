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

from shinobu.beacon.models import driver

class BeaconDriverManager:
    def __init__(self):
        self._drivers: dict = {}

    @property
    def platforms(self) -> list:
        return list(self._drivers.keys())

    def register_driver(self, platform: str, driver_object: driver.BeaconDriver):
        if platform in self._drivers:
            raise KeyError("Platform driver already registered")

        self._drivers.update({platform: driver_object})

    def remove_driver(self, platform: str):
        if platform not in self._drivers:
            raise KeyError("Platform driver not registered")

        self._drivers.pop(platform)

    def get_driver(self, platform: str) -> driver.BeaconDriver:
        return self._drivers.get(platform)