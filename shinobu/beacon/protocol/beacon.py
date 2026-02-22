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
import uuid
from enum import Enum
from discord.ext import bridge
from shinobu.beacon.protocol import (drivers as beacon_drivers, spaces as beacon_spaces, messages as beacon_messages,
                                     filters as beacon_filters)
from shinobu.beacon.models import (space as beacon_space, message as beacon_message, content as beacon_content,
                                   filter as beacon_filter, member as beacon_member, channel as beacon_channel,
                                   driver as beacon_driver)
from shinobu.runtime.secrets import fine_grained

# Set start method to fork
# This is not supported on Windows
if sys.platform != "win32":
    aiomultiprocess.set_start_method("fork")

class BeaconMessageBlockedReason(Enum):
    bridge_paused = 1
    filter_blocked = 2

class Beacon:
    def __init__(self, bot: bridge.Bot, files_wrapper: fine_grained.FineGrainedSecureFiles, enable_multi: bool = True):
        self._enable_multi: bool = enable_multi
        self.__wrapper: fine_grained.FineGrainedSecureFiles = files_wrapper
        self.__bot: bridge.Bot = bot

        # Initialize managers
        self._drivers: beacon_drivers.BeaconDriverManager = beacon_drivers.BeaconDriverManager()
        self._spaces: beacon_spaces.BeaconSpaceManager = beacon_spaces.BeaconSpaceManager()
        self._messages: beacon_messages.BeaconMessageCache = beacon_messages.BeaconMessageCache(self.__wrapper)
        self._filters: beacon_filters.BeaconFilterManager = beacon_filters.BeaconFilterManager()

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
    def bacon():
        """Bacon because I keep confusing beacon and bacon"""
        print("Bacon 🥓")

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

    async def can_send(self, author: beacon_member.BeaconMember,
                        space: beacon_space.BeaconSpace, content: beacon_message.BeaconMessageContent,
                        webhook_id: str | None = None, skip_filter: bool = False) -> BeaconMessageBlockedReason | None:
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
        # Filter scans should only be skipped when this is being ran by platform support cogs
        # as a preliminary check on whether they should continue with the bridge or not
        if not skip_filter:
            for filter_id in space.filters:
                if not filter_id in self._filters.filters:
                    # Filter doesn't exist or isn't loaded for whatever reason
                    continue

                filter_config: dict = space.filter_configs[filter_id]
                filter_data: dict = self._filters.get_filter_data(filter_id, author.server_id)
                filter_obj: beacon_filter.BeaconFilter = self._filters.get_filter(filter_id)

                # Assemble beacon data
                passed_data: dict = {
                    "config": filter_config,
                    "data": filter_data
                }

                # Run filter
                result: beacon_filter.BeaconFilterResult = await self.__bot.loop.run_in_executor(
                    None, filter_obj.check, author, content, webhook_id, passed_data
                )

                if not result.allowed and not result.safe_content:
                    return BeaconMessageBlockedReason.filter_blocked

                if not result.allowed and result.safe_content:
                    # Substitute content

                    for block_id in content.blocks:
                        block: beacon_content.BeaconContentBlock = content.blocks[block_id]

                        if type(block) is beacon_content.BeaconContentText:
                            content.remove_block(block_id)

                    # Create new filtered text block
                    filtered_block: beacon_content.BeaconContentText = beacon_content.BeaconContentText(result.safe_content)
                    content.add_block("filtered_block", filtered_block)

        # If we haven't returned by here, there's no problems with the content (or problems have
        # been addressed)
        return None

    async def _send_platform(self, driver: beacon_driver.BeaconDriver, author: beacon_member.BeaconMember,
                             space: beacon_space.BeaconSpace, content: beacon_message.BeaconMessageContent,
                             replies: list[beacon_message.BeaconMessage] | None = None, webhook_id: str | None = None
                             ) -> list[beacon_message.BeaconMessage]:
        space_members: list[beacon_space.BeaconSpaceMember] = [
            member for member in space.members if member.platform == driver.platform
        ]
        tasks = []

        for member in space_members:
            tasks.append(driver.send(member.channel, content, replies, author, webhook_id))

        if driver.supports_multi:
            results: list[beacon_message.BeaconMessage] = await self._strategy_multi(tasks, return_exceptions=True)
        elif driver.supports_async:
            results: list[beacon_message.BeaconMessage] = await self._strategy_async(tasks, return_exceptions=True)
        else:
            results: list[beacon_message.BeaconMessage] = await self._strategy_sequential(tasks)

        # Filter out exceptions
        for result in results:
            if type(result) is not beacon_message.BeaconMessage:
                results.remove(result)

        return results

    async def send(self, author: beacon_member.BeaconMember, space: beacon_space.BeaconSpace,
                   content: beacon_message.BeaconMessageContent,
                   replies: list[beacon_message.BeaconMessage] | None = None, webhook_id: str | None = None
                   ) -> beacon_message.BeaconMessageGroup:
        """Sends a message to a Space."""

        # Ensure we can send the message
        blocking_condition: BeaconMessageBlockedReason | None = await self.can_send(author, space, content, webhook_id)

        if blocking_condition:
            raise ValueError("Message blocked from being sent.")

        # Get the server's space membership
        space_membership: beacon_space.BeaconSpaceMember = space.get_member(author.server)

        # We'll re-fetch the channel just to check for age-gate status updates
        origin_driver: beacon_driver.BeaconDriver = self._drivers.get_driver(author.platform)
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(space_membership.channel_id)

        if (
                (space.nsfw and not channel.nsfw) or
                (not space.nsfw and channel.nsfw) or
                (space.nsfw and not origin_driver.supports_agegate)
        ):
            raise ValueError("Age gate mismatch.")

        # Send message for each platform
        tasks = []
        for platform in self._drivers.platforms:
            driver = self._drivers.get_driver(platform)
            tasks.append(self._send_platform(driver, author, space, content, replies, webhook_id))

        # Bridge to platforms
        results: list[list[beacon_message.BeaconMessage]] = await self._strategy_async(tasks, return_exceptions=True)

        # Assemble to beacon_message list
        results_final: list[beacon_message.BeaconMessage] = []
        for result in results:
            results_final.extend(result)

        # Convert replies to message groups
        replies_groups: list[str] = []
        for reply in replies:
            # Check if there's a message group with this message
            group: beacon_message.BeaconMessageGroup = self._messages.get_group_from_message(reply.id)

            if group:
                replies_groups.append(group.id)

        # Create message group
        message_group: beacon_message.BeaconMessageGroup = beacon_message.BeaconMessageGroup(
            group_id=str(uuid.uuid4()),
            author=author,
            space_id=space.id,
            messages=results_final,
            replies=replies_groups
        )

        # Cache message group
        self._messages.add_message(message_group)

        # Return group
        return message_group
