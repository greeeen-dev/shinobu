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

from shinobu.beacon.models import messageable, server as beacon_server

class BeaconChannel(messageable.BeaconMessageable):
    """A class representing server channels."""

    def __init__(self, channel_id: str, platform: str, name: str, server: beacon_server.BeaconServer,
                 nsfw: bool = False):
        super().__init__(channel_id, platform, name)
        self._server: beacon_server.BeaconServer = server
        self._nsfw: bool = nsfw

    @property
    def server(self) -> beacon_server.BeaconServer:
        return self._server

    @property
    def server_id(self) -> str:
        return self._server.id

    @property
    def nsfw(self) -> bool:
        return self._nsfw
