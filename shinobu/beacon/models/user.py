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

from shinobu.beacon.models import messageable

class BeaconUser(messageable.BeaconMessageable):
    """A class representing users."""

    def __init__(self, user_id: str, platform: str, name: str, display_name: str | None = None,
                 avatar_url: str | None = None, bot: bool = False):
        super().__init__(user_id, platform, name)
        self._display_name: str | None = display_name
        self._avatar: str | None = avatar_url
        self._bot: bool = bot

    @property
    def display_name(self) -> str:
        return self._display_name or self._name

    @property
    def avatar_url(self) -> str | None:
        return self._avatar

    @property
    def bot(self) -> bool:
        return self._bot
