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

from enum import Enum

class BeaconContentType(Enum):
    text = 10
    file = 13
    embed = 24

class BeaconContentBlock:
    """A class representing content blocks in a Beacon message."""

    def __init__(self, content_type: BeaconContentType, content: dict):
        self._type: BeaconContentType = content_type
        self._content: dict = content

    @property
    def type(self) -> BeaconContentType:
        return self._type

    @property
    def content(self) -> dict:
        return self._content

class BeaconContentText(BeaconContentBlock):
    def __init__(self, content: str):
        super().__init__(BeaconContentType.text, {"content": content})

    @property
    def content(self) -> str:
        return self._content["content"]

class BeaconContentEmbed(BeaconContentBlock):
    def __init__(self, title: str | None = None, description: str | None = None, url: str | None = None,
                 color: int | None = None, colour: int | None = None):
        super().__init__(BeaconContentType.embed, {
            "title": title, "description": description, "url": url, "color": color or colour, "fields": [],
            "author": {"text": None, "url": None, "icon_url": None}, "footer": {"text": None, "icon_url": None},
            "timestamp": None, "thumbnail": None, "media": None
        })

    # Title
    @property
    def title(self) -> str | None:
        """The title of the embed."""
        return self._content["title"]

    @title.setter
    def title(self, value: str | None):
        self._content["title"] = value

    # Description
    @property
    def description(self) -> str | None:
        """The description of the embed."""
        return self._content["description"]

    @description.setter
    def description(self, value: str | None):
        self._content["description"] = value

    # URL
    @property
    def url(self) -> str | None:
        """The URL of the embed."""
        return self._content["url"]

    @url.setter
    def url(self, value: str | None):
        self._content["url"] = value

    # Color (or colour)
    @property
    def color(self) -> int | None:
        """The color of the embed."""
        return self._content["color"]

    @color.setter
    def color(self, value: int | None):
        self._content["color"] = value

    @property
    def colour(self) -> int | None:
        """Alias for BeaconContentEmbed.color"""
        return self.color

    @colour.setter
    def colour(self, value: int | None):
        self.color = value

    # Fields
    @property
    def fields(self) -> list:
        """The raw fields data."""

        return self._content["fields"]

    # Author (or header)
    @property
    def author(self) -> dict:
        """The raw author/header data."""

        return self._content["author"]

    # Footer
    @property
    def footer(self) -> dict:
        """The raw footer data."""

        return self._content["footer"]

    # Thumbnail
    @property
    def thumbnail(self) -> str | None:
        """The thumbnail that will be displayed for the embed."""

        return self._content["thumbnail"]

    @thumbnail.setter
    def thumbnail(self, value: str | None):
        self._content["thumbnail"] = value

    # Media
    @property
    def media(self) -> str | None:
        """The media that will be displayed for the embed."""

        return self._content["media"]

    @media.setter
    def media(self, value: str | None):
        self._content["media"] = value

    # Timestamp
    @property
    def timestamp(self) -> int | None:
        """The timestamp that will be displayed for the embed."""

        return self._content["timestamp"]

    @timestamp.setter
    def timestamp(self, value: int | None):
        self._content["timestamp"] = value

    def add_field(self, name: str, value: str, inline: bool = False):
        """Adds a field."""

        self._content["fields"].append({"name": name, "value": value, "inline": inline})

    def remove_field(self, index: int):
        """Removes a field at a given index."""

        self._content["fields"].pop(index)

    def insert_field(self, index: int, name: str, value: str, inline: bool = False):
        """Inserts a field to a given index."""

        self._content["fields"].insert(index, {"name": name, "value": value, "inline": inline})

    def clear_fields(self):
        """Clears embed fields."""

        self._content["fields"] = []

    def set_author(self, text: str | None = None, url: str | None = None, icon_url: str | None = None):
        """Sets the author/header text and icon."""

        self._content["author"] = {
            "text": text,
            "url": url,
            "icon_url": icon_url
        }

    def set_footer(self, text: str | None = None, icon_url: str | None = None):
        """Sets the footer text and icon."""

        self._content["footer"] = {
            "text": text,
            "icon_url": icon_url
        }
