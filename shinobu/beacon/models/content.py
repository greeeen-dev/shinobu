from enum import Enum

class BeaconContentType(Enum):
    text = 1
    file = 2

class BeaconContentBlock:
    """A class representing content blocks in a Beacon message."""

    def __init__(self, content_type: BeaconContentType, content: dict):
        self._type: BeaconContentType = content_type
        self._content: dict = content

    @property
    def type(self) -> BeaconContentType:
        return self._type

    @property
    def content(self) -> dict:
        return self._content

class BeaconContentText(BeaconContentBlock):
    def __init__(self, content: str):
        super().__init__(BeaconContentType.text, {"content": content})
