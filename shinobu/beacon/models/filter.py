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

from shinobu.beacon.models import message as beacon_message

class BeaconMissingFilter(Exception):
    pass

class BeaconMissingCheck(Exception):
    pass

class BeaconFilterResult:
    def __init__(self, allowed: bool, data: dict | None = None, message: str | None = None,
                 should_log: bool = False, should_contribute: bool = False, safe_content: str | None = None):
        self.__allowed: bool = allowed # Whether the message can be bridged or not
        self.__data: dict = data or {} # Data to store in the temporary storage
        self.__message: str | None = message # Message to show if allowed is False and should_log is True
        self.__should_log: bool = should_log # Whether filter detection should be logged or not
        self.__should_contribute: bool = should_contribute # Whether filter detection should contribute to auto UAM or not
        self.__safe_content: str | None = safe_content # Substitute content to send if allowed is False

    @property
    def allowed(self):
        return self.__allowed

    @property
    def data(self):
        return self.__data

    @property
    def message(self):
        return self.__message or 'A filter blocked your message.'

    @property
    def should_log(self):
        return self.__should_log

    @property
    def should_contribute(self):
        return self.__should_contribute

    @property
    def safe_content(self):
        return self.__safe_content

class BeaconFilterConfig:
    types = {
        'string': str,
        'number': int,
        'integer': int,
        'float': float,
        'boolean': bool,
    }

    def __init__(self, name: str, description: str, config_type, limits: tuple | None = None, default=None):
        self.__name: str = name
        self.__description: str = description
        self.__type = config_type
        self.__limits: tuple | None = limits
        self.__default = default

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str:
        return self.__description

    @property
    def type(self):
        return self.__type

    @property
    def limits(self) -> tuple | None:
        return self.__limits

    @property
    def default(self):
        return self.__default

class BeaconFilter:
    def __init__(self, filter_id, name, description):
        self.__id: str = filter_id
        self.__name: str = name
        self.__description: str = description
        self.__configs: dict = {}

    @property
    def id(self) -> str:
        return self.__id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str:
        return self.__description

    @property
    def configs(self) -> dict:
        return self.__configs

    def add_config(self, config_id, config: BeaconFilterConfig):
        if config_id in self.__configs:
            raise ValueError('config already exists')

        self.__configs.update({config_id: config})

    def check(self, message: beacon_message.BeaconMessageContent, data) -> BeaconFilterResult:
        """Checks if a content is allowed or not allowed by the filter."""
        raise BeaconMissingFilter()
