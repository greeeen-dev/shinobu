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

import os
import ujson as json
import discord
from discord.ext import bridge

class ShinobuSharedObjects:
    def __init__(self):
        self._data: dict = {}

    def add(self, key: str, shared_object):
        if key in self._data:
            raise KeyError("Key already assigned to a shared object")

        self._data.update({key: shared_object})

    def get(self, key: str):
        return self._data.get(key)

class ShinobuBot(bridge.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__shared_objects: ShinobuSharedObjects = ShinobuSharedObjects()
        self.__cog_entitlements_loader = None

        # Get manifest
        self._manifest: str | None = None
        if "manifest" in kwargs:
            self._manifest = kwargs["manifest"]

        # Load events handler (this doesn't need entitlements)
        self.load_extension("shinobu.runtime.modules.events")
        self.load_extension("shinobu.runtime.modules.admin")

    def setup_entitlements_loader(self, loader):
        if self.__cog_entitlements_loader:
            raise RuntimeError("Cog loader already registered")

        self.__cog_entitlements_loader = loader

    def load_builtins(self):
        if not self.__cog_entitlements_loader:
            raise RuntimeError("Cog loader not registered yet")

        # Load builtin modules (separate from runtime modules)
        with open(self._manifest) as file:
            data: dict = json.load(file)

        for module in data["modules"]:
            self.__cog_entitlements_loader.load_extension(module)

    @property
    def shared_objects(self):
        return self.__shared_objects

    @property
    def cog_entitlements_loader(self):
        return self.__cog_entitlements_loader
