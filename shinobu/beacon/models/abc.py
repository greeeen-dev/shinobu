class BeaconABC:
    """A abstract base class for objects."""

    def __init__(self, object_id: str, platform: str):
        self._id: str = object_id
        self._platform: str = platform

    @property
    def id(self) -> str:
        """Returns the ID of an object."""
        return self._id

    @property
    def platform(self) -> str:
        """Returns the platform of an object."""
        return self._platform