from shinobu.beacon.models import abc

class BeaconServer(abc.BeaconABC):
    """A class representing a server."""

    def __init__(self, object_id: str, platform: str, name: str):
        super().__init__(object_id, platform)
        self._name: str = name

    @property
    def name(self) -> str:
        return self._name
