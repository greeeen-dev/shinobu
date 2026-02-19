from shinobu.beacon.protocol import drivers
from shinobu.runtime.secrets import fine_grained

class Beacon:
    def __init__(self, files_wrapper: fine_grained.FineGrainedSecureFiles):
        self._drivers = drivers.BeaconDriverManager()
        self.__wrapper: fine_grained.FineGrainedSecureFiles = files_wrapper

    @property
    def drivers(self) -> drivers.BeaconDriverManager:
        return self._drivers
