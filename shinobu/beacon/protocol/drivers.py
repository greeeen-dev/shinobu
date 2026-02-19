from shinobu.beacon.models import driver

class BeaconDriverManager:
    def __init__(self):
        self._drivers: dict = {}

    @property
    def platforms(self) -> list:
        return list(self._drivers.keys())

    def register_driver(self, platform: str, driver_object: driver.BeaconDriver):
        if platform in self._drivers:
            raise KeyError("Platform driver already registered")

        self._drivers.update({platform: driver_object})

    def remove_driver(self, platform: str):
        if platform not in self._drivers:
            raise KeyError("Platform driver not registered")

        self._drivers.pop(platform)

    def get_driver(self, platform: str) -> driver.BeaconDriver:
        return self._drivers.get(platform)