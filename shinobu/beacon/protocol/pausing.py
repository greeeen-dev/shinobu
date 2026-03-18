"""
Shinobu - Converse from anywhere, anytime.
Copyright (C) 2026-present  Green (@greeeen-dev)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

class BeaconPauseManager:
    def __init__(self):
        self._data: dict = {}

    def add_pause(self, user_id: str, mode: str = "inclusive", matches: list[dict[str, str]] | None = None):
        self._data.update({user_id: {"enabled": False, "mode": mode, "matches": matches or []}})

    def add_pause_from_dict(self, user_id: str, data: dict):
        self.add_pause(user_id, mode=data.get("mode", "inclusive"), matches=data.get("matches", []))
        self.set_pause(user_id, state=data.get("enabled", False))

    def remove_pause(self, user_id: str):
        self._data.pop(user_id, None)

    def set_pause(self, user_id: str, state: bool = False):
        if user_id not in self._data:
            return

        self._data["user_id"].update({"enabled": state})

    def check_can_send(self, user_id: str, content: str):
        if user_id not in self._data:
            return True

        if not self._data["user_id"]["enabled"]:
            return True

        matches: int = len([match for match in self._data["user_id"]["matches"]
                            if content.startswith(match["prefix"]) and content.startswith(match["suffix"])])

        if self._data["user_id"]["mode"] == "inclusive":
            return matches == 0
        else:
            return matches > 0

    def to_dict(self) -> dict:
        return self._data