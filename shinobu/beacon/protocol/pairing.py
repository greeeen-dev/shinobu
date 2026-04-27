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

from shinobu.beacon.models import emoji as beacon_emoji

class BeaconPairing:
    """Represents a server pairing group."""

    def __init__(self, group_id: str):
        self._id: str = group_id
        self._servers: dict = {}
        self._partial_servers: list = []

    @property
    def id(self) -> str:
        return self._id

    @property
    def servers(self) -> list:
        return list(self._servers.values())

    def add_server(self, server):
        server.pair(self._id)
        self._servers.update({server.id: server})
        self.add_partial_server(server.id, server.platform)

    def add_partial_server(self, server_id: str, platform: str):
        self._partial_servers.append({"id": server_id, "platform": platform})

    def remove_server(self, server):
        server.unpair(self._id)
        self._servers.pop(server.id)
        self.remove_partial_server(server.id)

    def remove_partial_server(self, server_id: str):
        for server in self._partial_servers:
            if server["id"] == server_id:
                self._partial_servers.remove(server)
                break

    def get_matches_for(self, server):
        origin_emojis: list[beacon_emoji.BeaconEmoji] = server.emojis
        origin_emojis_mapping: dict[str, beacon_emoji.BeaconEmoji] = {}

        mapping: dict[str, dict[str, beacon_emoji.BeaconEmoji]] = {}
        all_target_emojis: list[beacon_emoji.BeaconEmoji] = []

        # Get all emojis
        for target_server in self.servers:
            all_target_emojis = all_target_emojis + target_server.emojis

        # Create mappings
        for emoji in origin_emojis:
            mapping.update({emoji.id: {}})
            origin_emojis_mapping.update({emoji.name: emoji})

        for target_emoji in all_target_emojis:
            if target_emoji.name in origin_emojis_mapping:
                emoji: beacon_emoji.BeaconEmoji = origin_emojis_mapping[target_emoji.name]
                mapping[emoji.id].update({target_emoji.server_id: target_emoji})

        return mapping

    def to_dict(self):
        return {
            "id": self.id,
            "servers": self._partial_servers.copy()
        }

class BeaconPairingManager:
    def __init__(self):
        self._scheme_version: int = 1
        self._pairings: dict[str, BeaconPairing] = {}

    @property
    def pairings(self) -> list[BeaconPairing]:
        return list(self._pairings.values())

    def add_pairing(self, pairing: BeaconPairing):
        """Adds a Beacon server pair."""
        self._pairings.update({pairing.id: pairing})

    def remove_pairing(self, pairing_id: str):
        self._pairings.pop(pairing_id)

    def get_pairing(self, group_id: str) -> BeaconPairing:
        return self._pairings.get(group_id)

    def to_dict(self) -> dict:
        data = {}

        for pairing, pairing_obj in self._pairings.items():
            data[pairing] = pairing_obj.to_dict()

        return data
