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

from shinobu.beacon.models import abc, server as beacon_server, channel as beacon_channel

class BeaconWebhook(abc.BeaconABC):
    """A class representing server webhooks."""

    def __init__(self, webhook_id: str, platform: str, server: beacon_server.BeaconServer,
                 channel: beacon_channel.BeaconChannel | None = None):
        super().__init__(webhook_id, platform)
        self._server: beacon_server.BeaconServer = server
        self._channel: beacon_channel.BeaconChannel | None = channel

    @property
    def server(self) -> beacon_server.BeaconServer:
        return self._server

    @property
    def server_id(self) -> str:
        return self._server.id

    @property
    def channel(self) -> beacon_channel.BeaconChannel | None:
        return self._channel

    @property
    def channel_id(self) -> str:
        return self._channel.id
