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
        self._data_groups: dict[str, beacon_message.BeaconMessageGroup] = {}

    @property
    def cache_limit(self) -> int:
        return self._cache_limit

    @property
    def messages(self) -> int:
        return len(self._data.keys())

    def add_message(self, message: beacon_message.BeaconMessage | beacon_message.BeaconMessageGroup):
        target_dict = self._data_groups if type(message) is beacon_message.BeaconMessageGroup else self._data

        if message.id in target_dict.keys():
            raise ValueError("Message already cached")

        if len(target_dict.keys()) > self.cache_limit:
            target_dict.pop(next(iter(target_dict)))

        if type(message) is beacon_message.BeaconMessageGroup:
            if len(self._data_groups.keys()) > self.cache_limit:
                self._data_groups.pop(next(iter(self._data_groups)))

            self._data_groups.update({message.id: message})
        else:
            if len(self._data.keys()) > self.cache_limit:
                self._data.pop(next(iter(self._data)))

            self._data.update({message.id: message})

        # Save data
        self.save()

    def get_message(self, message_id: str) -> beacon_message.BeaconMessage | None:
        """Gets a message from the cache."""
        return self._data.get(message_id)

    def get_message_group(self, group_id: str) -> beacon_message.BeaconMessageGroup | None:
        """Gets a message from the cache."""
        return self._data_groups.get(group_id)

    def get_group_from_message(self, message_id: str) -> beacon_message.BeaconMessageGroup | None:
        """Gets a message group from the cache."""

        for _, group in self._data_groups.items():
            matches = [message for _, message in group.messages.items() if message.id == message_id]

            if len(matches) > 0:
                return group

        return None

    def save(self):
        """Saves cache as an encrypted file."""

        # Convert data to dictionary
        converted = {}
        for message in self._data:
            converted.update({message: self._data[message].to_dict()})

        converted_groups = {}
        for group in self._data_groups:
            converted_groups.update({group: self._data_groups[group].to_dict()})

        # Save data as JSON
        self.__wrapper.save_json("cache", {
            "messages": converted, "groups": converted_groups
        })
