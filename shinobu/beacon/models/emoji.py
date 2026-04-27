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

from shinobu.beacon.models import abc

class BeaconEmoji(abc.BeaconABC):
    """A abstract base class for objects."""

    def __init__(self, emoji_id: str, platform: str, name: str, server_id: str, emoji_text: str | None = None,
                 animated: bool = False):
        super().__init__(emoji_id, platform)
        self._name: str = name
        self._server_id: str = server_id
        self._animated: bool = animated
        self._emoji_text: str = emoji_text or (
            f"<a:{name}:{emoji_id}>" if animated else f"<:{name}:{emoji_id}>"
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def animated(self) -> bool:
        return self._animated

    @property
    def text(self) -> str:
        """The text for this emoji.
        If none was provided at instantiation, this will default to Discord's format."""
        return self._emoji_text
