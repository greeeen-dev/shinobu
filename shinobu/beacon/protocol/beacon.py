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

import sys
import asyncio
import aiomultiprocess
from enum import Enum
from shinobu.beacon.protocol import drivers as beacon_drivers, spaces as beacon_spaces, messages as beacon_messages
from shinobu.beacon.models import (space as beacon_space, message as beacon_message, content as beacon_content,
                                   user as beacon_user)
from shinobu.runtime.secrets import fine_grained

# Set start method to fork
# This is not supported on Windows
if sys.platform != "win32":
    aiomultiprocess.set_start_method("fork")

class BeaconMessageBlockedReason(Enum):
    bridge_paused = 1
    filter_blocked = 2

class Beacon:
    def __init__(self, files_wrapper: fine_grained.FineGrainedSecureFiles, enable_multi: bool = True):
        self._enable_multi: bool = enable_multi
        self.__wrapper: fine_grained.FineGrainedSecureFiles = files_wrapper

        # Initialize managers
        self._drivers: beacon_drivers.BeaconDriverManager = beacon_drivers.BeaconDriverManager()
        self._spaces: beacon_spaces.BeaconSpaceManager = beacon_spaces.BeaconSpaceManager()
        self._messages: beacon_messages.BeaconMessageCache = beacon_messages.BeaconMessageCache(self.__wrapper)

        # Get data
        self._data: dict = self.__wrapper.read_json("bridge")

        # Create aiomultiprocess pool if available and enabled
        self._pool: aiomultiprocess.Pool | None = None

        if sys.platform != "win32" and self._enable_multi:
            self._pool = aiomultiprocess.Pool()

    @property
    def drivers(self) -> beacon_drivers.BeaconDriverManager:
        return self._drivers

    @property
    def spaces(self) -> beacon_spaces.BeaconSpaceManager:
        return self._spaces

    @property
    def messages(self) -> beacon_messages.BeaconMessageCache:
        return self._messages

    @staticmethod
    async def _strategy_sequential(callbacks: list) -> list:
        """Sequentially executes asynchronous callbacks."""

        results = []
        for callback in callbacks:
            result = await callback()
            results.append(result)

        return results

    @staticmethod
    async def _strategy_async(callbacks: list, return_exceptions: bool = False) -> list:
        """Concurrently executes asynchronous callbacks."""

        return await asyncio.gather(*callbacks, return_exceptions=return_exceptions)

    async def _strategy_multi(self, callbacks: list, return_exceptions: bool = False) -> list:
        """Uses aiomultiprocess to execute asynchronous callbacks in parallel.
        Falls back to _strategy_async if unavailable."""

        if not self._pool:
            # Pool doesn't exist, multicore is likely unavailable or disabled.
            # Fallback to standard async
            return await self._strategy_async(callbacks, return_exceptions=return_exceptions)

        tasks = []

        for callback in callbacks:
            tasks.append(self._pool.apply(callback))

        # Run tasks in pool (and return result)
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    async def _can_send(self, author: beacon_user.BeaconUser, space: beacon_space.BeaconSpace,
                        content: beacon_message.BeaconMessageContent) -> BeaconMessageBlockedReason | None:
        # Get bridge paused data
        bridge_paused: dict = self._data.get("bridge_paused")

        # Does the author have their bridge paused?
        if author.id in bridge_paused:
            # Get bridge pause data
            bridge_paused_data: dict = bridge_paused[author.id]
            bridge_paused_inclusive: bool = bridge_paused_data.get("inclusive")
            bridge_paused_entries: list = bridge_paused_data.get("entries", [])

            # Check if there's any prefix and suffix matches
            has_match: bool = False
            content_text: str = content.to_plaintext()
            for entry in bridge_paused_entries:
                if (
                        content_text.startswith(entry["prefix"]) and
                        content_text.endswith(entry["suffix"]) and
                        bridge_paused_inclusive
                ):
                    # There's a prefix and suffix match here
                    return BeaconMessageBlockedReason.bridge_paused
                elif not bridge_paused_inclusive:
                    has_match = True
                    break

            if not has_match and not bridge_paused_inclusive:
                return BeaconMessageBlockedReason.bridge_paused

        # Run filter scans


    async def send(self, author: beacon_user.BeaconUser, space: beacon_space.BeaconSpace,
                   content: beacon_message.BeaconMessageContent) -> beacon_message.BeaconMessageGroup:
        """Sends a message to a Space."""

        pass
