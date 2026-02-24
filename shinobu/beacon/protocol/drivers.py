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
    def __init__(self, platform_whitelist: bool, allowed_platforms: list | None):
        self._drivers: dict = {}
        self._reserved: list = []
        self._whitelist: bool = platform_whitelist
        self._allowed_platforms: list = allowed_platforms or []
        self._setup_callback = None

    @property
    def platforms(self) -> list:
        return list(self._drivers.keys())

    @property
    def uses_platform_whitelist(self) -> bool:
        return self._whitelist

    @property
    def allowed_platforms(self) -> list:
        return self._allowed_platforms

    @property
    def has_reserved(self) -> bool:
        return len(self._reserved) > 0

    def register_driver(self, platform: str, driver_object: driver.BeaconDriver):
        if self.uses_platform_whitelist and not platform in self.allowed_platforms:
            raise ValueError("Platform not in whitelist")

        if platform in self._drivers:
            raise KeyError("Platform driver already registered")

        if platform in self._reserved:
            self._reserved.remove(platform)

        self._drivers.update({platform: driver_object})

        if len(self._reserved) == 0 and self._setup_callback:
            self._setup_callback()

    def remove_driver(self, platform: str, silent: bool = False):
        if platform not in self._drivers:
            if silent:
                return
            raise KeyError("Platform driver not registered")

        self._drivers.pop(platform)

    def get_driver(self, platform: str) -> driver.BeaconDriver:
        return self._drivers.get(platform)

    def reserve_driver(self, platform: str):
        if self.uses_platform_whitelist and not platform in self.allowed_platforms:
            raise ValueError("Platform not in whitelist")

        if not platform in self._reserved:
            self._reserved.append(platform)

    def unreserve_driver(self, platform: str):
        if platform in self._reserved:
            self._reserved.remove(platform)

        if len(self._reserved) == 0 and self._setup_callback:
            self._setup_callback()

    def set_setup_callback(self, callback):
        if not self._setup_callback:
            self._setup_callback = callback
