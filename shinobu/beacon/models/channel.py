from shinobu.beacon.models import messageable, server as beacon_server

class BeaconChannel(messageable.BeaconMessageable):
    """A class representing server channels."""

    def __init__(self, object_id: str, platform: str, name: str, server: beacon_server.BeaconServer,
                 nsfw: bool = False):
        super().__init__(object_id, platform, name)
        self._server: beacon_server.BeaconServer = server
        self._nsfw: bool = nsfw

    @property
    def server(self) -> beacon_server.BeaconServer:
        return self._server

    @property
    def server_id(self) -> str:
        return self._server.id

    @property
    def nsfw(self) -> bool:
        return self._nsfw
