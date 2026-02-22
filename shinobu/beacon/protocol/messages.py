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

from shinobu.runtime.secrets import fine_grained
from shinobu.beacon.models import message as beacon_message

class BeaconMessageCache:
    def __init__(self, wrapper: fine_grained.FineGrainedSecureFiles, cache_limit: int = 10000):
        self.__wrapper: fine_grained.FineGrainedSecureFiles = wrapper
        self._cache_limit = cache_limit
        self._data: dict[str, beacon_message.BeaconMessage] = {}

    @property
    def cache_limit(self) -> int:
        return self._cache_limit

    @property
    def messages(self) -> int:
        return len(self._data.keys())

    def add_message(self, message: beacon_message.BeaconMessage):
        if message.id in self._data.keys():
            raise ValueError("Message already cached")

        if len(self._data.keys()) > self.cache_limit:
            self._data.pop(next(iter(self._data)))

        self._data.update({message.id: message})

    def get_message(self, message_id: str) -> beacon_message.BeaconMessage | None:
        """Gets a message from the cache."""

        # Strategy 1: direct fetch from dict
        message = self._data.get(message_id)

        if message:
            return message

        # Strategy 2: fetch from message object
        results = [entry for _, entry in self._data.items() if entry.id == message_id]

        if len(results) > 0:
            return results[0]

        # Otherwise, return nothing
        return None

    def save(self):
        """Saves cache as an encrypted file."""

        # Convert data to dictionary
        converted = {}
        for message in self._data:
            converted.update({message: self._data[message].to_dict()})

        # Save data as JSON
        self.__wrapper.save_json("bridge", self._data)
