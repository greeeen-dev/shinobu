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

class BeaconABC:
    """A abstract base class for objects."""

    def __init__(self, object_id: str, platform: str):
        self._id: str = object_id
        self._platform: str = platform

    @property
    def id(self) -> str:
        """Returns the ID of an object."""
        return self._id

    @property
    def platform(self) -> str:
        """Returns the platform of an object."""
        return self._platform