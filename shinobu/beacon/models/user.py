from shinobu.beacon.models import messageable

class BeaconUser(messageable.BeaconMessageable):
    """A class representing users."""

    def __init__(self, object_id: str, platform: str, name: str, display_name: str | None = None,
                 avatar_url: str | None = None):
        super().__init__(object_id, platform, name)
        self._display_name: str | None = display_name
        self._avatar: str | None = avatar_url

    @property
    def display_name(self) -> str:
        return self._display_name or self._name

    @property
    def avatar_url(self) -> str | None:
        return self._avatar
