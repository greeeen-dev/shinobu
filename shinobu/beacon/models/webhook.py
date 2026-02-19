from shinobu.beacon.models import abc, server as beacon_server, channel as beacon_channel

class BeaconWebhook(abc.BeaconABC):
    """A class representing server webhooks."""

    def __init__(self, object_id: str, platform: str, server: beacon_server.BeaconServer,
                 channel: beacon_channel.BeaconChannel | None = None):
        super().__init__(object_id, platform)
        self._server: beacon_server.BeaconServer = server
        self._channel: beacon_channel.BeaconChannel | None = channel

    @property
    def server(self) -> beacon_server.BeaconServer:
        return self._server

    @property
    def server_id(self) -> str:
        return self._server.id

    @property
    def channel(self) -> beacon_channel.BeaconChannel | None:
        return self._channel

    @property
    def channel_id(self) -> str:
        return self._channel.id
