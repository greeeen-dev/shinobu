from shinobu.beacon.models import (user as beacon_user, channel as beacon_channel, server as beacon_server,
                                   member as beacon_member, webhook as beacon_webhook, message as beacon_message,
                                   messageable as beacon_messageable)

class BeaconDriverUnsupported(Exception):
    def __init__(self):
        super().__init__("Driver does not support this feature.")

class BeaconDriverWebhookCache:
    def __init__(self):
        self._data: dict = {}

    def store_webhook(self, webhook: beacon_webhook.BeaconWebhook):
        if webhook.id in self._data:
            raise KeyError("Webhook already in cache")

        self._data.update({webhook.id: webhook})

    def store_webhooks(self, webhooks: list):
        for webhook in webhooks:
            self.store_webhook(webhook)

    def get_webhook(self, webhook_id: str):
        return self._data.get(webhook_id)

class BeaconDriver:
    """A class representing a platform driver for the Beacon bridge protocol."""

    def __init__(self, platform: str, bot):
        self._platform: str = platform
        self._webhooks: BeaconDriverWebhookCache = BeaconDriverWebhookCache()
        self._bot = bot

    @property
    def platform(self) -> str:
        """The platform the driver enables support for."""
        return self._platform

    def get_user(self, user_id: str) -> beacon_user.BeaconUser:
        """Gets a user."""
        raise BeaconDriverUnsupported()

    async def fetch_user(self, user_id: str) -> beacon_user.BeaconUser:
        """Fetches a user from the platform API."""
        raise BeaconDriverUnsupported()

    def get_member(self, server: beacon_server.BeaconServer, member_id: str) -> beacon_member.BeaconMember:
        """Gets a member from a server."""
        raise BeaconDriverUnsupported()

    def get_channel(self, server: beacon_server.BeaconServer, channel_id: str) -> beacon_channel.BeaconChannel:
        """Gets a channel from a server."""
        raise BeaconDriverUnsupported()

    def get_server(self, server_id: str) -> beacon_server.BeaconServer:
        """Gets a server."""
        raise BeaconDriverUnsupported()

    async def fetch_server(self, server_id: str) -> beacon_server.BeaconServer:
        """Fetches a server from the platform API."""
        raise BeaconDriverUnsupported()

    def get_webhook(self, webhook_id: str) -> beacon_webhook.BeaconWebhook:
        """Gets a webhook."""

        # Many libraries don't have a built-in webhook cache, so Beacon provides its own.
        # However, this method can still be overwritten as needed.

        return self._webhooks.get_webhook(webhook_id)

    async def fetch_webhook(self, webhook_id: str) -> beacon_webhook.BeaconWebhook:
        """Fetches a webhook from the platform API."""

        # Preferrably this should call self._webhooks.store_webhook(webhook) after fetching the webhook
        # to store the webhook to cache, unless the library has a webhook cache of its own.

        raise BeaconDriverUnsupported()

    async def send(self, destination: beacon_messageable.BeaconMessageable,
                   content: beacon_message.BeaconMessageContent, send_as: beacon_user.BeaconUser):
        """Sends a message to a given destination."""
        raise BeaconDriverUnsupported()
