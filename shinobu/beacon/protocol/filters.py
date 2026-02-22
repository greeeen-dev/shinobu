import copy
from shinobu.beacon.models import filter as beacon_filter

class BeaconFilterManager:
    def __init__(self):
        self._filters: dict[str, beacon_filter.BeaconFilter] = {}
        self._filter_data: dict[str, dict] = {}

    @property
    def filters(self) -> list:
        return list(self._filters.keys())

    def add_filter(self, filter_obj: beacon_filter.BeaconFilter):
        if filter_obj.id in self._filters:
            raise ValueError("Filter already registered")

        self._filters.update({filter_obj.id: filter_obj})

    def get_filter(self, filter_id: str):
        return self._filters.get(filter_id)

    def get_filter_data(self, filter_id: str, server_id: str):
        return self._filter_data.get(filter_id, {}).get(server_id)

    def save_filter_data(self, filter_id: str, server_id: str, data: dict):
        if not self._filter_data.get(filter_id):
            self._filter_data.update({filter_id: {}})

        self._filter_data[filter_id].update({server_id: copy.copy(data)})
