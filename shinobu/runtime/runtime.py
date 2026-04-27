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

import tomllib
import ujson as json
import discord
from discord.ext import bridge
from shinobu.runtime.models import colors

class ShinobuErrorManager:
    def __init__(self):
        self._data: dict = {}

    def add(self, error_id: str, traceback: str, data: dict):
        if error_id in self._data:
            return

        self._data.update({error_id: {"traceback": traceback, "data": data}})

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
        self.__errors: ShinobuErrorManager = ShinobuErrorManager()
        self.__cog_entitlements_loader = None
        self._cleanups = {}
        self._colors: colors.Colors = colors.Colors()
        self._version: str = kwargs.get("version", "0.0.0")

        # Restart state
        self._should_restart: bool = False # Restart on crash
        self._requested_restart: bool = False # Instance owner requested restart
        self.restart_message_id: int | None = None
        self.restart_message_channel_id: int | None = None

        # Load configs
        self._config: dict = {}
        try:
            with open("configs/main.toml", "rb") as file:
                self._config = tomllib.load(file)
        except (FileNotFoundError, tomllib.TOMLDecodeError):
            pass

        # Set auto-restart on crash
        self._should_restart = self._config.get("system", {}).get("restart_on_crash")

        # Get manifest
        self._manifest: str | None = None
        if "manifest" in kwargs:
            self._manifest = kwargs["manifest"]

        # Load events handler (this doesn't need entitlements)
        self.load_extension("shinobu.runtime.modules.events")
        self.load_extension("shinobu.runtime.modules.admin")
        self.load_extension("shinobu.runtime.modules.general")

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

    def add_cleanup_func(self, func_name: str, func):
        if func_name in self._cleanups:
            raise ValueError("Cleanup function already registered")

        self._cleanups.update({func_name: func})

    def remove_cleanup_func(self, func_name: str):
        self._cleanups.pop(func_name, None)

    def cleanup(self):
        current_index: int = 1
        total: int = len(self._cleanups)
        for name, cleanup_func in self._cleanups.items():
            print(f"Cleaning up runtime. ({name}, {current_index}/{total})")

            # noinspection PyBroadException
            try:
                cleanup_func()
            except:
                # For the sake of letting other cleanup functions run, we'll ignore the error
                pass

            current_index += 1

    @property
    def config(self) -> dict:
        return self._config

    @property
    def version(self) -> str:
        return self._version

    @property
    def colors(self) -> colors.Colors:
        return self._colors

    @property
    def should_restart(self) -> bool:
        return self._should_restart

    @property
    def requested_restart(self) -> bool:
        return self._requested_restart

    @property
    def shared_objects(self) -> ShinobuSharedObjects:
        return self.__shared_objects

    @property
    def errors(self) -> ShinobuErrorManager:
        return self.__errors

    @property
    def cog_entitlements_loader(self):
        return self.__cog_entitlements_loader

    def request_restart(self, message: discord.Message | None = None):
        """Sets bot to restart. This does not restart the bot on its own."""
        self._requested_restart = True

        if message:
            self.restart_message_id = message.id
            self.restart_message_channel_id = message.channel.id
