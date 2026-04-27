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

import time
from Crypto.Random import random
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

    @property
    def partial_servers(self) -> list:
        return self._partial_servers.copy()

    def add_server(self, server):
        if server.pairing == self.id:
            # Assume paired
            return
        
        server.pair(self._id)
        self._servers.update({server.id: server})
        self.add_partial_server(server.id, server.platform)

    def add_partial_server(self, server_id: str, platform: str):
        if self.has_partial_entry(server_id, platform):
            return
        
        self._partial_servers.append({"id": server_id, "platform": platform})

    def upgrade_partial_server(self, server):
        if server.id in self._servers:
            return

        has_partial: bool = self.has_partial_entry(server.id, server.platform)

        if has_partial:
            self._servers.update({server.id: server})
            server.pair(self._id)

    def remove_server(self, server):
        server.unpair()
        self._servers.pop(server.id)
        self.remove_partial_server(server.id, server.platform)

    def remove_partial_server(self, server_id: str, platform: str):
        for server in self._partial_servers:
            if server["id"] == server_id and server["platform"] == platform:
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
            mapping.update({emoji.text: {}})
            origin_emojis_mapping.update({emoji.name: emoji})

        for target_emoji in all_target_emojis:
            if target_emoji.name in origin_emojis_mapping:
                emoji: beacon_emoji.BeaconEmoji = origin_emojis_mapping[target_emoji.name]
                mapping[emoji.text].update({target_emoji.platform: target_emoji})

        return mapping

    def has_partial_entry(self, server_id: str, platform: str):
        has_partial: bool = False
        for partial_server in self._partial_servers:
            if partial_server["id"] == server_id and partial_server["platform"] == platform:
                has_partial = True
                break

        return has_partial

    def to_dict(self):
        return {
            "id": self.id,
            "servers": self._partial_servers.copy()
        }

class BeaconPairingManager:
    def __init__(self):
        self._scheme_version: int = 1
        self._pairings: dict[str, BeaconPairing] = {}
        self._pairing_codes: dict = {}
        self._server_mapping: dict[str, dict[str, str]] = {}

    @property
    def pairings(self) -> list[BeaconPairing]:
        return list(self._pairings.values())

    @staticmethod
    def _generate_unique_code() -> str:
        """Generates a pairing code using CSPRNG."""
        return "".join([str(random.randint(0, 9)) for _ in range(10)])

    def new_pairing_code(self, server) -> str:
        code: str = self._generate_unique_code()
        self._pairing_codes.update({code: {"server": server, "expiry": round(time.time()) + 1800}})
        return code

    def get_pairing_code_server(self, code: str):
        pairing_info: dict | None = self._pairing_codes.get(code)
        if not pairing_info:
            return

        if pairing_info["expiry"] < time.time():
            self.revoke_pairing_code(code)
            return

        return pairing_info["server"]

    def revoke_pairing_code(self, code: str):
        self._pairing_codes.pop(code, None)

    def add_pairing(self, pairing: BeaconPairing):
        """Adds a Beacon server pair."""
        self._pairings.update({pairing.id: pairing})
        self.update_pairing(pairing.id)

    def update_pairing(self, pairing_id: str):
        pairing: BeaconPairing | None = self._pairings.get(pairing_id)
        if not pairing:
            return

        for server in pairing.partial_servers:
            if server["platform"] not in self._server_mapping:
                self._server_mapping.update({server["platform"]: {}})

            self._server_mapping[server["platform"]].update({server["id"]: pairing.id})

    def remove_server_mapping(self, server):
        self._server_mapping.get(server["platform"], {}).pop(server["id"], None)

    def remove_pairing(self, pairing_id: str):
        self._pairings.pop(pairing_id)

    def get_pairing(self, group_id: str) -> BeaconPairing | None:
        return self._pairings.get(group_id)

    def get_pairing_for_server(self, server_id, platform) -> BeaconPairing | None:
        pairing_id: str | None = self._server_mapping.get(platform, {}).get(server_id)
        if not pairing_id:
            return None

        pairing: BeaconPairing = self.get_pairing(pairing_id)
        if pairing.has_partial_entry(server_id, platform):
            return pairing

    def to_dict(self) -> dict:
        data = {}

        for pairing, pairing_obj in self._pairings.items():
            if len(pairing_obj.partial_servers) == 0:
                continue

            data[pairing] = pairing_obj.to_dict()

        return data
