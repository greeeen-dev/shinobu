from shinobu.beacon.models import filter as beacon_filter

class BeaconFilterManager:
    def __init__(self):
        self._filters: dict[str, beacon_filter.BeaconFilter]
        self._filter_data: dict[str, dict]


