from shinobu.beacon.models import (content as beacon_content, abc, user as beacon_user, channel as beacon_channel,
                                   server as beacon_server, webhook as beacon_webhook)

class BeaconMessageContent:
    def __init__(self):
        self._blocks: dict = {}

    def to_plaintext(self) -> str:
        components: list = []
        for block in self._blocks:
            block_obj: beacon_content.BeaconContentBlock = self._blocks[block]

            # We'll restrict blocks to BeaconContentText only here
            if type(block_obj) is not beacon_content.BeaconContentBlock:
                continue

            components.append(block_obj.content)

        return "\n".join(components)

class BeaconMessage(abc.BeaconABC):
    def __init__(self, message_id: str, platform: str, author: beacon_user.BeaconUser | beacon_webhook.BeaconWebhook,
                 server: beacon_server.BeaconServer | None = None, channel: beacon_channel.BeaconChannel | None = None,
                 content: str | dict | None = None):
        super().__init__(message_id, platform)
        self._author: beacon_user.BeaconUser | beacon_webhook.BeaconWebhook = author
        self._server: beacon_server.BeaconServer | None = server
        self._channel: beacon_channel.BeaconChannel | None = channel
        self._content: str | dict | None = content

    @property
    def author(self) -> beacon_user.BeaconUser | beacon_webhook.BeaconWebhook:
        return self._author

    @property
    def webhook(self) -> beacon_webhook.BeaconWebhook | None:
        if type(self._author) is not beacon_webhook.BeaconWebhook:
            return None

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

    def edit_content(self, new_content: str | dict | None):
        self._content = new_content

    def to_dict(self, include_content: bool = False) -> dict:
        """Returns a BeaconMessage object as a dictionary. Should be used for backing up
        Beacon state."""
        converted = {
            "id": self.id,
            "platform": self.platform,
            "author_id": self.author.id,
            "server_id": self.server.id if self.server else None,
            "channel_id": self.channel.id if self.channel else None,
            "webhook_id": self.webhook.id if self.webhook else None
        }

        if include_content:
            converted.update({"content": self.content})

        return converted
