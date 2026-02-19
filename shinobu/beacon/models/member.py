from shinobu.beacon.models import user, server as beacon_server

class BeaconMember(user.BeaconUser):
    """A class representing server members."""

    def __init__(self, object_id: str, platform: str, name: str, server: beacon_server.BeaconServer,
                 display_name: str | None = None, avatar_url: str | None = None):
        super().__init__(object_id, platform, name, display_name=display_name, avatar_url=avatar_url)
        self._server: beacon_server.BeaconServer = server

    @property
    def server(self) -> beacon_server.BeaconServer:
        return self._server

    @property
    def server_id(self) -> str:
        return self._server.id
