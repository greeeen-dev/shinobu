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

from shinobu.beacon.models import abc, emoji as beacon_emoji

class BeaconServer(abc.BeaconABC):
    """A class representing a server."""

    def __init__(self, server_id: str, platform: str, name: str, filesize_limit: int | None = None,
                 emojis: list[beacon_emoji.BeaconEmoji] | None = None):
        super().__init__(server_id, platform)
        self._name: str = name
        self._filesize_limit: int | None = filesize_limit
        self._emojis: list[beacon_emoji.BeaconEmoji] = emojis or []
        self._pairing: str | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def filesize_limit(self) -> int | None:
        return self._filesize_limit

    @property
    def emojis(self) -> list[beacon_emoji.BeaconEmoji]:
        return self._emojis

    @property
    def pairing(self) -> str | None:
        return self._pairing

    def pair(self, pair_id: str):
        """Pairs a server with a pairing group."""
        self._pairing = pair_id

    def unpair(self):
        self._pairing = None

    def __eq__(self, other):
        if not isinstance(other, BeaconServer):
            return False

        return self.id == other.id
