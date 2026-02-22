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

from shinobu.beacon.models import (content as beacon_content, abc, user as beacon_user, channel as beacon_channel,
                                   server as beacon_server, webhook as beacon_webhook, file as beacon_file,
                                   messageable as beacon_messageable)

class BeaconMessageContent:
    def __init__(self, original_id: str, original_channel_id: str, blocks: dict[str, beacon_content.BeaconContentBlock],
                 files: list[beacon_file.BeaconFile] | None = None, replies: list['BeaconMessageGroup'] | None = None,
                 reply_content: str | None = None, reply_attachments: int | None = None):
        self._original_id: str = original_id
        self._original_channel_id: str = original_channel_id
        self._blocks: dict[str, beacon_content.BeaconContentBlock] = blocks
        self._files: list[beacon_file.BeaconFile] = files or []
        self._replies: list[BeaconMessageGroup] = replies or []
        self._reply_content: str | None = reply_content
        self._reply_attachments: int = reply_attachments or 0

    @property
    def original_id(self) -> str:
        return self._original_id

    @property
    def original_channel_id(self) -> str:
        return self._original_channel_id

    @property
    def blocks(self) -> dict[str, beacon_content.BeaconContentBlock]:
        return self._blocks

    @property
    def files(self) -> list[beacon_file.BeaconFile]:
        return self._files

    @property
    def replies(self) -> list['BeaconMessageGroup']:
        return self._replies

    @property
    def reply_content(self) -> str | None:
        return self._reply_content

    @property
    def reply_attachments(self) -> int:
        return self._reply_attachments

    def add_block(self, block_id: str, block: beacon_content.BeaconContentBlock):
        if block_id in self._blocks:
            raise ValueError("Block already in blocks")

        self._blocks.update({block_id: block})

    def remove_block(self, block_id):
        self._blocks.pop(block_id)

    def to_plaintext(self) -> str:
        components: list = []
        for block in self._blocks:
            block_obj: beacon_content.BeaconContentBlock = self._blocks[block]

            # We'll restrict blocks to BeaconContentText only here
            if type(block_obj) is not beacon_content.BeaconContentBlock:
                continue

            components.append(block_obj.content)

        return "\n".join(components)

class BeaconLegacyMessageContent:
    def __init__(self):
        self._content: str = ""
        self._files: list = []
        self._embeds: list = []

class BeaconMessageGroup:
    """A class representing a group of BeaconMessage objects.
    This is to be used to store bridged messages in the cache."""

    def __init__(self, group_id: str, author: beacon_user.BeaconUser | str, space_id: str,
                 messages: list['BeaconMessage'], replies: list[str]):
        self._id: str = group_id
        self._author: beacon_user.BeaconUser | None = author if type(author) is beacon_user.BeaconUser else None
        self._author_id: str | None = author if type(author) is str else None
        self._space_id: str = space_id
        self._messages: dict[str, BeaconMessage] = {}
        self._replies: list[str] = replies

        for message in messages:
            self._messages.update({message.id: message})

    @property
    def id(self) -> str:
        return self._id

    @property
    def author(self) -> beacon_user.BeaconUser:
        return self._author

    @property
    def author_id(self) -> str:
        return self._author.id if self._author else self._author_id

    @property
    def messages(self) -> dict:
        return self._messages

    @property
    def replies(self) -> list:
        return self._replies

    def get_message_for(self, messageable: beacon_messageable.BeaconMessageable) -> 'BeaconMessage | None':
        for _, message in self._messages.items():
            if message.channel.id == messageable.id:
                return message

        return None

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "author": self.author_id,
            "space": self._space_id,
            "messages": {}
        }

        for message in self._messages:
            data["messages"].update({message: self._messages[message].to_dict()})

        return data

class BeaconMessage(abc.BeaconABC):
    def __init__(self, message_id: str, platform: str, author: beacon_user.BeaconUser,
                 server: beacon_server.BeaconServer | None = None, channel: beacon_channel.BeaconChannel | None = None,
                 content: str | dict | None = None, attachments: int = 0, replies: list['BeaconMessage'] | None = None,
                 webhook_id: str | None = None):
        super().__init__(message_id, platform)
        self._author: beacon_user.BeaconUser = author
        self._server: beacon_server.BeaconServer | None = server
        self._channel: beacon_channel.BeaconChannel | None = channel
        self._content: str | dict | None = content
        self._attachments: int = attachments
        self._replies: list[BeaconMessage] = replies or []
        self._webhook_id: str | None = webhook_id

    @property
    def author(self) -> beacon_user.BeaconUser | beacon_webhook.BeaconWebhook:
        return self._author

    @property
    def server(self) -> beacon_server.BeaconServer | None:
        return self._server

    @property
    def channel(self) -> beacon_channel.BeaconChannel | None:
        return self._channel

    @property
    def content(self) -> str | dict | None:
        return self._content

    @property
    def attachments(self) -> int:
        return self._attachments

    @property
    def webhook_id(self) -> str:
        return self._webhook_id

    def edit_content(self, new_content: str | dict | None):
        self._content = new_content

    def to_dict(self, include_content: bool = False) -> dict:
        """Returns a BeaconMessage object as a dictionary. Should be used for backing up
        Beacon state."""

        converted: dict = {
            "id": self.id,
            "platform": self.platform,
            "author_id": self.author.id,
            "server_id": self.server.id if self.server else None,
            "channel_id": self.channel.id if self.channel else None,
            "webhook_id": self.webhook_id
        }

        converted.update({"replies": [reply.id for reply in self._replies]})

        # NOTE: include_content is NOT recommended to be used if not necessary for the sake
        # of minimizing data stored on-disk (even if encrypted).
        if include_content:
            converted.update({"content": self.content})

        return converted
