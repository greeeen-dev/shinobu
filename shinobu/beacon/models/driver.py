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

from shinobu.beacon.protocol import messages as beacon_messages
from shinobu.beacon.models import (user as beacon_user, channel as beacon_channel, server as beacon_server,
                                   member as beacon_member, webhook as beacon_webhook, message as beacon_message,
                                   messageable as beacon_messageable)

class BeaconDriverUnsupported(Exception):
    def __init__(self):
        super().__init__("Driver does not support this feature.")

class BeaconDriverPlatformMismatch(Exception):
    def __init__(self, platform: str):
        super().__init__(f"Driver does not support platform {platform}.")

class BeaconDriverWebhookCache:
    """Built-in driver webhook cache.
    This is only for caching platform webhooks and not BeaconWebhooks."""

    def __init__(self):
        self._data: dict = {}

    def store_webhook(self, webhook_id: str, webhook):
        if webhook.id in self._data:
            raise KeyError("Webhook already in cache")

        self._data.update({webhook_id: webhook})

    def store_webhooks(self, webhooks: dict):
        for webhook in webhooks:
            self.store_webhook(webhook, webhooks[webhook])

    def get_webhook(self, webhook_id: str):
        return self._data.get(webhook_id)

class BeaconDriver:
    """A class representing a platform driver for the Beacon bridge protocol."""

    def __init__(self, platform: str, bot, message_cache: beacon_messages.BeaconMessageCache):
        self._platform: str = platform
        self._webhooks: BeaconDriverWebhookCache = BeaconDriverWebhookCache()
        self._bot = bot
        self._messages: beacon_messages.BeaconMessageCache = message_cache

        # Configs (override this in your platform driver subclass as needed)
        self._supports_multi: bool = True # Enable multicore processing via aiomultiprocess. Must support async
        self._supports_async: bool = True # Enable concurrent processing via asyncio tasks
        self._supports_agegate: bool = False # Allow age-gated Spaces to be bridged to the platform.
        self._file_limit: int = 26214400 # Filesize limit for the platform. This can be overriden by server limits if available
        self._file_count_limit: int = 10  # File count for the platform.

    def get_user(self, user_id: str) -> beacon_user.BeaconUser | None:
        """Gets a user."""
        raise BeaconDriverUnsupported()

    async def fetch_user(self, user_id: str) -> beacon_user.BeaconUser:
        """Fetches a user from the platform API."""
        raise BeaconDriverUnsupported()

    def _get_member(self, server: beacon_server.BeaconServer, member_id: str) -> beacon_member.BeaconMember | None:
        """Gets a member from a server."""
        raise BeaconDriverUnsupported()

    def _get_channel(self, server: beacon_server.BeaconServer, channel_id: str) -> beacon_channel.BeaconChannel | None:
        """Gets a channel from a server."""
        raise BeaconDriverUnsupported()

    def get_server(self, server_id: str) -> beacon_server.BeaconServer | None:
        """Gets a server."""
        raise BeaconDriverUnsupported()

    async def fetch_server(self, server_id: str) -> beacon_server.BeaconServer:
        """Fetches a server from the platform API."""
        raise BeaconDriverUnsupported()

    def get_webhook(self, webhook_id: str) -> beacon_webhook.BeaconWebhook | None:
        """Gets a webhook."""
        raise BeaconDriverUnsupported()

    async def fetch_webhook(self, webhook_id: str) -> beacon_webhook.BeaconWebhook:
        """Fetches a webhook from the platform API."""

        # Preferrably this should call self._webhooks.store_webhook(webhook) after fetching the webhook
        # to store the webhook to cache, unless the library has a webhook cache of its own.

        raise BeaconDriverUnsupported()

    async def send(self, destination: beacon_messageable.BeaconMessageable,
                   content: beacon_message.BeaconMessageContent, replies: list[beacon_message.BeaconMessage],
                   send_as: beacon_user.BeaconUser | None = None, webhook_id: str | None = None
                   ) -> beacon_message.BeaconMessage:
        """Sends a message to a given destination."""
        raise BeaconDriverUnsupported()

    async def _edit(self, message: beacon_message.BeaconMessage, content: beacon_message.BeaconMessageContent):
        """Edits a message."""
        raise BeaconDriverUnsupported()

    async def _delete(self, message: beacon_message.BeaconMessage):
        """Deletes a message."""
        raise BeaconDriverUnsupported()

    def sanitize_inbound(self, content: str) -> str:
        """Sanitizes content to be friendly with the driver's platform."""
        raise BeaconDriverUnsupported()

    def sanitize_outbound(self, content: str) -> str:
        """Sanitizes content to be friendly with other platforms."""
        raise BeaconDriverUnsupported()

    # The following properties and methods are already implemented but can be overwritten
    # for custom behavior.

    async def getch_webhook(self, webhook_id: str) -> beacon_webhook.BeaconWebhook:
        """Gets or fetches a webhook."""

        return self._webhooks.get_webhook(webhook_id) or await self.fetch_webhook(webhook_id)

    # The following properties and methods are already implemented. It is strongly
    # recommended to leave them as-is unless you absolutely need to overwrite it.

    @property
    def platform(self) -> str:
        """The platform the driver enables support for."""
        return self._platform

    @property
    def supports_multi(self) -> bool:
        """Whether the driver supports multicore execution via aiomultiprocess."""
        return self._supports_multi and self._supports_async

    @property
    def supports_async(self) -> bool:
        """Whether the driver supports concurrent execution via asyncio."""
        return self._supports_async

    @property
    def supports_agegate(self) -> bool:
        return self._supports_agegate

    @property
    def file_count_limit(self) -> int:
        return self._file_count_limit

    def get_member(self, server: beacon_server.BeaconServer, member_id: str) -> beacon_member.BeaconMember | None:
        """Gets a member from a server."""

        # NOTE: You will need to overwrite BeaconDriver._get_member for this to work.

        if server.platform != self.platform:
            raise BeaconDriverPlatformMismatch(server.platform)

        return self._get_member(server, member_id)

    def get_channel(self, server: beacon_server.BeaconServer, channel_id: str) -> beacon_channel.BeaconChannel | None:
        """Gets a channel from a server."""

        # NOTE: You will need to overwrite BeaconDriver._get_channel for this to work.

        if server.platform != self.platform:
            raise BeaconDriverPlatformMismatch(server.platform)

        return self._get_channel(server, channel_id)

    def get_filesize_limit(self, server: beacon_server.BeaconServer | None = None) -> int:
        """Returns the filesize limit for the platform (or server-specific limits if a server
        is provided)."""

        if server:
            return server.filesize_limit if server.filesize_limit > self._file_limit else self._file_limit
        else:
            return self._file_limit

    async def edit(self, message: beacon_message.BeaconMessage, content: beacon_message.BeaconMessageContent):
        """Edits a message."""

        # NOTE: You will need to overwrite BeaconDriver._edit for this to work.

        if message.platform != self.platform:
            raise BeaconDriverPlatformMismatch(message.platform)

        return await self._edit(message, content)

    async def delete(self, message: beacon_message.BeaconMessage):
        """Deletes a message."""

        # NOTE: You will need to overwrite BeaconDriver._delete for this to work.

        if message.platform != self.platform:
            raise BeaconDriverPlatformMismatch(message.platform)

        return await self._delete(message)
