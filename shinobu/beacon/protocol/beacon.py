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
                                   driver as beacon_driver, server as beacon_server)
from shinobu.runtime.secrets import fine_grained

# Set start method to fork
# This is not supported on Windows
if sys.platform != "win32":
    aiomultiprocess.set_start_method("fork")

class BeaconMessageBlockedReason(Enum):
    bridge_paused = 1
    filter_blocked = 2

class BeaconNotInit(Exception):
    def __init__(self):
        super().__init__("The resource is not available because Beacon isn't ready yet.")

class Beacon:
    def __init__(self, bot: bridge.Bot, files_wrapper: fine_grained.FineGrainedSecureFiles, config: dict | None = None,
                 enable_multi: bool = True):
        self._enable_multi: bool = enable_multi and False # We'll clamp this to False for now
        self.__wrapper: fine_grained.FineGrainedSecureFiles = files_wrapper
        self.__bot: bridge.Bot = bot
        self._config: dict = config or {}
        self._init: bool = False

        # Get data
        self._data: dict = self.__wrapper.read_json("beacon").get("raw", {})

        # Initialize managers
        self._drivers: beacon_drivers.BeaconDriverManager = beacon_drivers.BeaconDriverManager(
            self._config.get("enable_platform_whitelist", False),
            self._config.get("enabled_platforms")
        )
        self._spaces: beacon_spaces.BeaconSpaceManager = beacon_spaces.BeaconSpaceManager()
        self._messages: beacon_messages.BeaconMessageCache = beacon_messages.BeaconMessageCache(self.__wrapper)
        self._filters: beacon_filters.BeaconFilterManager = beacon_filters.BeaconFilterManager()

        # Create aiomultiprocess pool if available and enabled
        self._pool: aiomultiprocess.Pool | None = None

        if sys.platform != "win32" and self._enable_multi:
            self._pool = aiomultiprocess.Pool()

    @property
    def initialized(self) -> bool:
        return self._init

    @property
    def config(self) -> dict:
        return self._config

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

    def load_data(self):
        if self.drivers.has_reserved:
            # Wait for all drivers to load
            self.drivers.set_setup_callback(self._load_data)
        else:
            self._load_data()

    def _load_data(self):
        if self.initialized:
            return

        # Get data from wrapper
        data: dict = self.__wrapper.read_json("beacon")

        # Load spaces
        # {'spaces': {'674f2cfe-7f02-422e-a4da-06951bb13152': {'id': '674f2cfe-7f02-422e-a4da-06951bb13152', 'name': 'test', 'emoji': None, 'members': [], 'invites': [], 'bans': [], 'options': {'private': False, 'nsfw': False, 'relay_deletes': True, 'relay_edits': True, 'convert_large_files': True}}}}
        for space_id, space_data in data.get("spaces", {}).items():
            space: beacon_space.BeaconSpace = beacon_space.BeaconSpace(
                space_id=space_id,
                space_name=space_data.get("name"),
                space_emoji=space_data.get("emoji"),
                private=space_data.get("options", {}).get("private"),
                private_owner_id=space_data.get("options", {}).get("private_owner_id"),
                nsfw=space_data.get("options", {}).get("nsfw"),
                relay_deletes=space_data.get("options", {}).get("relay_deletes"),
                relay_edits=space_data.get("options", {}).get("relay_edits"),
                relay_large_attachments=space_data.get("options", {}).get("convert_large_files"),
                filters=space_data.get("options", {}).get("filters"),
                filter_configs=space_data.get("options", {}).get("filter_configs")
            )

            # Import invites
            for invite in space_data.get("invites", []):
                space.add_invite(beacon_space.BeaconSpaceInvite.from_dict(invite))

            # Import members
            for member in space_data.get("members"):
                platform_driver: beacon_driver.BeaconDriver = self.drivers.get_driver(member["platform"])

                if not platform_driver:
                    # Join as "partial" member
                    space.partial_join(
                        platform=member["platform"],
                        server_id=member["server"],
                        channel_id=member["channel"],
                        webhook_id=member["webhook"],
                        invite=member["invite"]
                    )
                    continue

                # Get server
                server: beacon_server.BeaconServer | None = platform_driver.get_server(member["server"])

                if server:
                    channel: beacon_channel.BeaconChannel | None = platform_driver.get_channel(server, member["channel"])
                else:
                    # We can't import this server, so make a dummy server
                    server = beacon_server.BeaconServer(
                        server_id=member["server"],
                        platform=member["platform"],
                        name="Unknown server"
                    )
                    channel: beacon_channel.BeaconChannel | None = beacon_channel.BeaconChannel(
                        channel_id=member["channel"],
                        platform=member["platform"],
                        name="Unknown channel",
                        server=server
                    )

                # Add member entry
                space.join(
                    server=server,
                    channel=channel,
                    invite=member["invite"],
                    webhook=member["webhook"],
                    force=True
                )

            # Add space
            self.spaces.add_space(space)

        self._init = True
        print("Beacon is ready!")

    def save_data(self):
        if not self.initialized:
            raise BeaconNotInit()

        # Assemble data dict
        data: dict = {
            "spaces": self._spaces.to_dict(),
            "raw": self._data
        }

        self.__wrapper.save_json("beacon", data)

    async def can_send(self, author: beacon_member.BeaconMember,
                        space: beacon_space.BeaconSpace, content: beacon_message.BeaconMessageContent,
                        webhook_id: str | None = None, skip_filter: bool = False) -> BeaconMessageBlockedReason | None:
        if not self.initialized:
            raise BeaconNotInit()

        # Get bridge paused data
        bridge_paused: dict = self._data.get("bridge_paused", {})

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
                             self_send: bool = False) -> list[beacon_message.BeaconMessage]:
        space_members: list[beacon_space.BeaconSpaceMember] = [
            member for member in space.members if member.platform == driver.platform
        ]
        tasks = []

        for member in space_members:
            tasks.append(driver.send(
                member.channel, content, send_as=author, webhook_id=member.webhook_id, self_send=self_send
            ))

        if driver.supports_multi:
            results: list[beacon_message.BeaconMessage] = await self._strategy_multi(tasks, return_exceptions=False)
        elif driver.supports_async:
            results: list[beacon_message.BeaconMessage] = await self._strategy_async(tasks, return_exceptions=False)
        else:
            results: list[beacon_message.BeaconMessage] = await self._strategy_sequential(tasks)

        # Filter out exceptions
        for result in results:
            if type(result) is not beacon_message.BeaconMessage:
                results.remove(result)

        return results

    async def _edit_platform(self, driver: beacon_driver.BeaconDriver, message_group: beacon_message.BeaconMessageGroup,
                             content: beacon_message.BeaconMessageContent):
        platform_messages: list[beacon_message.BeaconMessage] = [
            message for _, message in message_group.messages.items() if message.platform == driver.platform
        ]
        tasks = []

        for message in platform_messages:
            tasks.append(driver.edit(message, content))

        if driver.supports_multi:
            await self._strategy_multi(tasks, return_exceptions=False)
        elif driver.supports_async:
            await self._strategy_async(tasks, return_exceptions=False)
        else:
            await self._strategy_sequential(tasks)

    async def _delete_platform(self, driver: beacon_driver.BeaconDriver,
                               message_group: beacon_message.BeaconMessageGroup, original: beacon_message.BeaconMessage
                               ):
        platform_messages: list[beacon_message.BeaconMessage] = [
            message for _, message in message_group.messages.items() if message.platform == driver.platform and
                                                                        message.id != original.id
        ]
        tasks = []

        for message in platform_messages:
            tasks.append(driver.delete(message))

        if driver.supports_multi:
            await self._strategy_multi(tasks, return_exceptions=False)
        elif driver.supports_async:
            await self._strategy_async(tasks, return_exceptions=False)
        else:
            await self._strategy_sequential(tasks)

    async def send(self, author: beacon_member.BeaconMember, space: beacon_space.BeaconSpace,
                   content: beacon_message.BeaconMessageContent, webhook_id: str | None = None
                   ) -> beacon_message.BeaconMessageGroup:
        """Sends a message to a Space."""

        if not self.initialized:
            raise BeaconNotInit()

        # Ensure we can send the message
        blocking_condition: BeaconMessageBlockedReason | None = await self.can_send(author, space, content, webhook_id)

        if blocking_condition:
            raise ValueError("Message blocked from being sent.")

        # Get the server's space membership
        space_membership: beacon_space.BeaconSpaceMember = space.get_member(author.server)

        # We'll re-fetch the channel just to check for age-gate status updates
        origin_driver: beacon_driver.BeaconDriver = self._drivers.get_driver(author.platform)
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(
            space_membership.server, space_membership.channel_id
        )

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
            tasks.append(self._send_platform(driver, author, space, content))

        # Bridge to platforms
        results: list[list[beacon_message.BeaconMessage]] = await self._strategy_async(tasks, return_exceptions=False)

        # Assemble to beacon_message list
        results_final: list[beacon_message.BeaconMessage] = []
        for result in results:
            if type(result) is list:
                for result_message in result:
                    if not type(result_message) is beacon_message.BeaconMessage:
                        continue

                    results_final.append(result_message)
                    self._messages.add_message(result_message)

        # Convert replies
        replies_groups: list[str] = []
        for reply in content.replies:
            replies_groups.append(reply.id)

        # Create message group
        message_group: beacon_message.BeaconMessageGroup = beacon_message.BeaconMessageGroup(
            group_id=str(uuid.uuid4()),
            author=author,
            space_id=space.id,
            messages=results_final,
            replies=replies_groups
        )

        # Cache message group
        await self.__bot.loop.run_in_executor(
            None, lambda: self._messages.add_message(message_group, save=True)
        )

        # Return group
        return message_group

    async def edit(self, message: beacon_message.BeaconMessage, content: beacon_message.BeaconMessageContent):
        """Edits a message sent to a Space."""

        if not self.initialized:
            raise BeaconNotInit()

        origin_driver: beacon_driver.BeaconDriver = self._drivers.get_driver(message.platform)

        # Get message metadata
        server: beacon_server.BeaconServer = message.server
        author: beacon_member.BeaconMember = origin_driver.get_member(server, message.author.id)

        # Get message group
        message_group: beacon_message.BeaconMessageGroup = self.messages.get_group_from_message(message.id)
        if not message_group:
            # We can't do anything with uncached messages
            return

        space: beacon_space.BeaconSpace = self.spaces.get_space(message_group.space_id)

        # Ensure we can send the message
        blocking_condition: BeaconMessageBlockedReason | None = await self.can_send(author, space, content)

        if blocking_condition:
            raise ValueError("Message blocked from being sent.")

        # Get the server's space membership
        space_membership: beacon_space.BeaconSpaceMember = space.get_member(author.server)

        # We'll re-fetch the channel just to check for age-gate status updates
        # noinspection DuplicatedCode
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(
            space_membership.server, space_membership.channel_id
        )

        if (
                (space.nsfw and not channel.nsfw) or
                (not space.nsfw and channel.nsfw) or
                (space.nsfw and not origin_driver.supports_agegate)
        ):
            raise ValueError("Age gate mismatch.")

        # Edit message for each platform
        tasks = []
        for platform in self._drivers.platforms:
            driver = self._drivers.get_driver(platform)
            tasks.append(self._edit_platform(driver, message_group, content))

        # Bridge to platforms
        await self._strategy_async(tasks, return_exceptions=False)

    async def delete(self, message: beacon_message.BeaconMessage):
        """Deletes a message sent to a Space."""

        if not self.initialized:
            raise BeaconNotInit()

        # Get message group
        message_group: beacon_message.BeaconMessageGroup = self.messages.get_group_from_message(message.id)
        if not message_group:
            # We can't do anything with uncached messages
            return

        # Edit message for each platform
        tasks = []
        for platform in self._drivers.platforms:
            driver = self._drivers.get_driver(platform)
            tasks.append(self._delete_platform(driver, message_group, message))

        # Bridge to platforms
        await self._strategy_async(tasks, return_exceptions=False)

        # Remove message group from cache
        await self.__bot.loop.run_in_executor(None, lambda: self.messages.remove_message_group(message_group))
