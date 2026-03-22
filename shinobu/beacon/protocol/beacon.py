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

import asyncio
import uuid
from enum import Enum
from discord.ext import bridge
from shinobu.beacon.protocol import (drivers as beacon_drivers, spaces as beacon_spaces, messages as beacon_messages,
                                     filters as beacon_filters, pausing as beacon_pausing)
from shinobu.beacon.models import (space as beacon_space, message as beacon_message, content as beacon_content,
                                   filter as beacon_filter, member as beacon_member, channel as beacon_channel,
                                   driver as beacon_driver, server as beacon_server, user as beacon_user)
from shinobu.runtime.secrets import fine_grained

class BeaconMessageBlockedReason(Enum):
    bridge_paused = 1
    filter_blocked = 2

class BeaconNotInit(Exception):
    def __init__(self):
        super().__init__("The resource is not available because Beacon isn't ready yet.")

class BeaconPlatformDisabled(Exception):
    def __init__(self, platform: str):
        super().__init__(f"The resource is not available because {platform} is disabled.")

class BeaconCallback:
    def __init__(self, func, args: list | None = None, kwargs: dict | None = None):
        self._func = func
        self._args: list = args or []
        self._kwargs: dict = kwargs or {}

    @property
    def coroutine(self):
        return self._func(*self._args, **self._kwargs)

    @property
    def func(self):
        return self._func

    @property
    def args(self) -> list:
        return self._args

    @property
    def kwargs(self) -> dict:
        return self._kwargs

class Beacon:
    def __init__(self, bot: bridge.Bot, files_wrapper: fine_grained.FineGrainedSecureFiles, config: dict | None = None,
                 enable_multi: bool = True):
        self._enable_multi: bool = enable_multi
        self.__wrapper: fine_grained.FineGrainedSecureFiles = files_wrapper
        self.__bot: bridge.Bot = bot
        self._config: dict = config or {}
        self._disabled_platforms: list[str] = []
        self._init: bool = False
        self._bridge_tasks: dict[str, list] = {}

        # Get data
        self._data: dict = self.__wrapper.read_json("beacon").get("raw", {})

        # Create message ID reservations
        self._pending: dict = {}

        # Create platforms that may need webhook cache wipe
        self._webhook_cache_wipe: list[str] = []

        # Initialize managers
        self._drivers: beacon_drivers.BeaconDriverManager = beacon_drivers.BeaconDriverManager(
            self._config.get("enable_platform_whitelist", False),
            self._config.get("enabled_platforms")
        )
        self._spaces: beacon_spaces.BeaconSpaceManager = beacon_spaces.BeaconSpaceManager()
        self._messages: beacon_messages.BeaconMessageCache = beacon_messages.BeaconMessageCache(self.__wrapper)
        self._filters: beacon_filters.BeaconFilterManager = beacon_filters.BeaconFilterManager()
        self._pausing: beacon_pausing.BeaconPauseManager = beacon_pausing.BeaconPauseManager()

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

    @property
    def disabled_platforms(self) -> list[str]:
        return self._disabled_platforms

    @property
    def pending_bridge_tasks(self) -> int:
        return len(self._bridge_tasks)

    @staticmethod
    def bacon():
        """Bacon because I keep confusing beacon and bacon"""
        print("Bacon 🥓")

    def enable_platform(self, platform: str):
        if platform not in self._drivers.platforms:
            raise ValueError("Driver not registered")
        if platform not in self._disabled_platforms:
            raise ValueError("Platform already enabled")

        self._disabled_platforms.remove(platform)

    def disable_platform(self, platform: str):
        if platform not in self._drivers.platforms:
            raise ValueError("Driver not registered")
        if platform in self._disabled_platforms:
            raise ValueError("Platform already disabled")

        self._disabled_platforms.append(platform)

    @staticmethod
    def _has_timeout(results: tuple | list):
        for result in results:
            if type(result) is asyncio.TimeoutError:
                return True

        return False

    @staticmethod
    async def _strategy_sequential(callbacks: list[BeaconCallback | Exception]) -> list:
        """Sequentially executes asynchronous callbacks."""

        results = []
        for callback in callbacks:
            async with asyncio.timeout(15):
                result = await callback.coroutine

            results.append(result)

        return results

    async def _strategy_async(self, callbacks: list[BeaconCallback | Exception], return_exceptions: bool = False) -> tuple:
        """Concurrently executes asynchronous callbacks."""

        tasks = [asyncio.create_task(callback.coroutine) for callback in callbacks]

        # Add task to tasks list
        self._bridge_tasks.update({str(uuid.uuid4()): [tasks]})

        async with asyncio.timeout(15 * len(callbacks)):
            return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    def cancel_pending_tasks(self):
        for task_entry in self._bridge_tasks:
            for task in self._bridge_tasks[task_entry]:
                if not isinstance(task, asyncio.Task):
                    continue

                task.cancel()

        self._bridge_tasks.clear()

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

        # Get cache from wrapper
        cache: dict = self.__wrapper.read_json("cache")

        # Load spaces
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
                compatibility=space_data.get("options", {}).get("compatibility"),
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
                    # Add "partial" member only
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
                channel: beacon_channel.BeaconChannel | None = None

                if server:
                    channel = platform_driver.get_channel(server, member["channel"])

                if not server or not channel:
                    # We can't import this server or channel, so we'll just have to add it as a partial member
                    space.partial_join(
                        platform=member["platform"],
                        server_id=member["server"],
                        channel_id=member["channel"],
                        webhook_id=member["webhook"],
                        invite=member["invite"]
                    )
                    continue

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

        # Load bridge pause data
        for user_id, user_pause_data in data.get("paused", {}).items():
            self._pausing.add_pause_from_dict(user_id, user_pause_data)

        # Load message cache
        for message_id, message_data in cache.get("messages", {}).items():
            origin_driver: beacon_driver.BeaconDriver = self._drivers.get_driver(message_data.get("origin_platform"))
            destination_driver: beacon_driver.BeaconDriver = self._drivers.get_driver(message_data.get("platform"))

            if not origin_driver or not destination_driver:
                continue

            user: beacon_user.BeaconUser = origin_driver.get_user(message_data.get("author_id"))
            server: beacon_server.BeaconServer = destination_driver.get_server(message_data.get("server_id"))
            channel: beacon_channel.BeaconChannel | None = destination_driver.get_channel(server, message_data.get("channel_id")) if server else None

            if not user or not server or not channel:
                continue

            message: beacon_message.BeaconMessage = beacon_message.BeaconMessage(
                message_id=message_id,
                platform=message_data.get("platform"),
                origin_platform=message_data.get("origin_platform"),
                author=user,
                server=server,
                channel=channel,
                webhook_id=message_data.get("webhook_id")
            )

            self.messages.add_message(message)

        # Load message groups
        for group_id, group_data in cache.get("groups", {}).items():
            group_messages: list[beacon_message.BeaconMessage] = []

            for message_id in group_data.get("messages", []):
                message: beacon_message.BeaconMessage | None = self.messages.get_message(message_id)

                if not message:
                    continue

                group_messages.append(message)

            group: beacon_message.BeaconMessageGroup = beacon_message.BeaconMessageGroup(
                group_id=group_id,
                author=group_data.get("author_id"),
                space_id=group_data.get("author_id"),
                messages=group_messages,
                replies=group_data.get("replies", [])
            )

            self.messages.add_message(group)

        self._init = True

        # Add shutdown cleanup
        # noinspection PyUnresolvedReferences
        self.__bot.add_cleanup_func("bridge-save-data", self.save_data)
        # noinspection PyUnresolvedReferences
        self.__bot.add_cleanup_func("bridge-save-cache", self.messages.save)

        print("Beacon is ready!")

    def save_data(self):
        if not self.initialized:
            raise BeaconNotInit()

        # Assemble data dict
        data: dict = {
            "spaces": self._spaces.to_dict(),
            "paused": self._pausing.to_dict(),
            "raw": self._data
        }

        self.__wrapper.save_json("beacon", data)

    def _reserve_message(self, message_id: str, group_id: str):
        self._pending.update({message_id: {"group_id": group_id, "callbacks": []}})

    def is_pending(self, message_id: str):
        return message_id in self._pending

    def add_callback(self, message_id: str, callback, args: list | None = None, kwargs: dict | None = None):
        if not self.is_pending(message_id):
            return

        self._pending[message_id]["callbacks"].append(BeaconCallback(callback, args, kwargs))

    def _cancel_pending_actions(self, message_id: str):
        self._pending.pop(message_id, None)

    async def _run_pending_actions(self, message_id: str):
        if not self.is_pending(message_id):
            return

        # Run pending tasks
        await self._strategy_sequential(self._pending[message_id]["callbacks"])

        # Remove reservation
        self._pending.pop(message_id)

    async def can_send(self, author: beacon_member.BeaconMember,
                        space: beacon_space.BeaconSpace, content: beacon_message.BeaconMessageContent,
                        webhook_id: str | None = None, skip_filter: bool = False) -> BeaconMessageBlockedReason | None:
        if not self.initialized:
            raise BeaconNotInit()

        # Does the author have their bridge paused?
        content_text: str = content.to_plaintext()
        if not self._pausing.check_can_send(author.id, content_text):
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
        tasks: list[BeaconCallback] = []

        for member in space_members:
            task: BeaconCallback = BeaconCallback(
                driver.send,
                [member.channel, content],
                {
                    "send_as": author, "webhook_id": member.webhook_id, "self_send": self_send,
                    "compatibility": True #space.compatibility
                }
            )
            tasks.append(task)

        try:
            if driver.supports_async:
                results: tuple[beacon_message.BeaconMessage] = await self._strategy_async(tasks, return_exceptions=False)
            else:
                results: list[beacon_message.BeaconMessage] = await self._strategy_sequential(tasks)
        except asyncio.TimeoutError:
            if driver.platform not in self._webhook_cache_wipe:
                self._webhook_cache_wipe.append(driver.platform)
            raise

        # Filter out exceptions
        for result in results:
            if type(result) is not beacon_message.BeaconMessage:
                results.remove(result)

        return results

    async def _edit_platform(self, driver: beacon_driver.BeaconDriver, message_group: beacon_message.BeaconMessageGroup,
                             content: beacon_message.BeaconMessageContent):
        platform_messages: list[beacon_message.BeaconMessage] = [
            message for _, message in message_group.messages.items() if message.platform == driver.platform and message.id != content.original_id
        ]
        tasks: list[BeaconCallback] = []

        space: beacon_space.BeaconSpace | None = self.spaces.get_space(message_group.space_id)
        compatibility: bool = False

        if space:
            compatibility = space.compatibility

        for message in platform_messages:
            task: BeaconCallback = BeaconCallback(
                driver.edit,
                [message, content],
                {"compatibility": compatibility}
            )
            tasks.append(task)

        if driver.supports_async:
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
            task: BeaconCallback = BeaconCallback(
                driver.delete,
                [message]
            )
            tasks.append(task)

        if driver.supports_async:
            await self._strategy_async(tasks, return_exceptions=False)
        else:
            await self._strategy_sequential(tasks)

    async def _purge_platform(self, driver: beacon_driver.BeaconDriver,
                              message_groups: list[beacon_message.BeaconMessageGroup]):
        platform_channel_messages: dict[str, list[beacon_message.BeaconMessage]] = {}

        # Get messages
        for message_group in message_groups:
            for message in message_group.messages.values():
                if message.platform != driver.platform:
                    continue

                if message.channel.id not in platform_channel_messages:
                    platform_channel_messages.update({message.channel.id: []})

                platform_channel_messages[message.channel.id].append(message)

        # Purge for each channel
        tasks = []
        for channel_messages in platform_channel_messages.values():
            task: BeaconCallback = BeaconCallback(
                driver.purge,
                [channel_messages]
            )
            tasks.append(task)

        if driver.supports_async:
            await self._strategy_async(tasks, return_exceptions=False)
        else:
            await self._strategy_sequential(tasks)

    async def send(self, author: beacon_member.BeaconMember, space: beacon_space.BeaconSpace,
                   content: beacon_message.BeaconMessageContent, webhook_id: str | None = None
                   ) -> beacon_message.BeaconMessageGroup | None:
        """Sends a message to a Space."""

        if not self.initialized:
            raise BeaconNotInit()

        if content.original_platform in self._disabled_platforms:
            raise BeaconPlatformDisabled(content.original_platform)

        # Get group ID
        group_id: str = str(uuid.uuid4())

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
            if platform in self._disabled_platforms:
                continue

            driver = self._drivers.get_driver(platform)
            task: BeaconCallback = BeaconCallback(
                self._send_platform,
                args=[driver, author, space, content]
            )
            tasks.append(task)

        # We'll "reserve" the message ID to let the delete methods know that we're waiting for the message
        # to bridge
        # This is useful when a message gets deleted before we can handle it
        self._reserve_message(content.original_id, group_id)

        # Bridge to platforms
        try:
            results: tuple[list[beacon_message.BeaconMessage] | Exception] = await self._strategy_async(tasks, return_exceptions=True)
        except:
            # Cancel pending actions
            self._cancel_pending_actions(content.original_id)
            raise

        if self._has_timeout(results):
            # Wipe webhook cache
            for should_wipe in self._webhook_cache_wipe:
                driver: beacon_driver.BeaconDriver = self._drivers.get_driver(should_wipe)
                driver.webhooks.clear_webhooks()
                self._webhook_cache_wipe.remove(should_wipe)

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
            group_id=group_id,
            author=author,
            space_id=space.id,
            messages=results_final,
            replies=replies_groups
        )

        # Cache message group
        # noinspection PyTypeChecker
        await self.__bot.loop.run_in_executor(
            None, lambda: self._messages.add_message(message_group, save=True)
        )

        # Run pending actions
        await self._run_pending_actions(content.original_id)

        # Return group
        return message_group

    async def edit(self, message: beacon_message.BeaconMessage, content: beacon_message.BeaconMessageContent):
        """Edits a message sent to a Space."""

        if not self.initialized:
            raise BeaconNotInit()

        if content.original_platform in self._disabled_platforms:
            raise BeaconPlatformDisabled(content.original_platform)

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
            if platform in self._disabled_platforms:
                continue

            driver = self._drivers.get_driver(platform)
            task: BeaconCallback = BeaconCallback(
                self._edit_platform,
                args=[driver, message_group, content]
            )
            tasks.append(task)

        # Bridge to platforms
        await self._strategy_async(tasks, return_exceptions=False)

    async def delete(self, message: beacon_message.BeaconMessage):
        """Deletes a message sent to a Space."""

        if not self.initialized:
            raise BeaconNotInit()

        if message.platform in self._disabled_platforms:
            raise BeaconPlatformDisabled(message.platform)

        # Get message group
        message_group: beacon_message.BeaconMessageGroup = self.messages.get_group_from_message(message.id)
        if not message_group:
            # We can't do anything with uncached messages
            return

        # Edit message for each platform
        tasks = []
        for platform in self._drivers.platforms:
            if platform in self._disabled_platforms:
                continue

            driver = self._drivers.get_driver(platform)
            task: BeaconCallback = BeaconCallback(
                self._delete_platform,
                args=[driver, message_group, message]
            )
            tasks.append(task)

        # Bridge to platforms
        await self._strategy_async(tasks, return_exceptions=False)

        # Remove message group from cache
        # noinspection PyTypeChecker
        await self.__bot.loop.run_in_executor(None, lambda: self.messages.remove_message_group(message_group))

    async def purge(self, messages: list[beacon_message.BeaconMessage]):
        """Purges messages sent to a Space."""

        if not self.initialized:
            raise BeaconNotInit()

        if messages[0].platform in self._disabled_platforms:
            raise BeaconPlatformDisabled(messages[0].platform)

        # Get message groups
        message_groups: list[beacon_message.BeaconMessageGroup] = []
        for message in messages:
            message_group: beacon_message.BeaconMessageGroup = self.messages.get_group_from_message(message.id)
            if not message_group:
                # We can't do anything with uncached messages
                return

            message_groups.append(message_group)

        # Edit message for each platform
        tasks = []
        for platform in self._drivers.platforms:
            if platform in self._disabled_platforms:
                continue

            driver = self._drivers.get_driver(platform)
            task: BeaconCallback = BeaconCallback(
                self._purge_platform,
                args=[driver, message_groups]
            )
            tasks.append(task)

        # Bridge to platforms
        await self._strategy_async(tasks, return_exceptions=False)

        # Remove message groups from cache
        for message_group in message_groups:
            # noinspection PyTypeChecker
            await self.__bot.loop.run_in_executor(None, lambda: self.messages.remove_message_group(message_group))
