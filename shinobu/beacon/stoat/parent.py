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
import traceback
import stoat
from discord.ext import commands
from stoat.ext import commands as stoat_commands
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.stoat import driver as stoat_driver
from shinobu.beacon.models import (driver as beacon_driver, file as beacon_file, content as beacon_content,
                                   message as beacon_message, server as beacon_server, channel as beacon_channel,
                                   member as beacon_member, space as beacon_space)

class StoatBot(stoat_commands.Bot):
    def __init__(self, beacon_obj: beacon.Beacon, driver_obj: stoat_driver.StoatDriver, *args,
                 owner_id: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._beacon: beacon.Beacon = beacon_obj
        self._driver: stoat_driver.StoatDriver = driver_obj
        self.owner_id: str | None = owner_id # imagine having @commands.is_owner() but not Bot.owner_id. how "suckless"
        self.owner_ids: list = [owner_id] if owner_id else []

        # Notification on whether the event handlers are working or not
        self.messages_working_notif: bool = False

    @property
    def beacon(self) -> beacon.Beacon:
        return self._beacon

    def register_driver(self):
        if "stoat" not in self._beacon.drivers.platforms:
            self._beacon.drivers.register_driver("stoat", self._driver)

    async def add_extensions(self):
        await self.load_extension("shinobu.beacon.stoat.modules.frontend")

    async def _to_beacon_content(self, message: stoat.Message | stoat.PartialMessage) -> beacon_message.BeaconMessageContent:
        # Create text content block
        text_content: beacon_content.BeaconContentText = beacon_content.BeaconContentText(
            content=self._driver.sanitize_outbound(str(message.content))
        )

        # Create embed blocks
        embed_blocks: list[beacon_content.BeaconContentEmbed] = []
        for embed in message.embeds:
            embed_block: beacon_content.BeaconContentEmbed = beacon_content.BeaconContentEmbed(
                title=embed.title,
                description=embed.description,
                url=embed.url,
                color=embed.color
            )

            # Add to embed blocks
            embed_blocks.append(embed_block)

        # Get replies
        replies: list[beacon_message.BeaconMessageGroup] = []
        replies_content: dict = {}
        replies_attachments: dict = {}

        if isinstance(message, stoat.Message):
            for reply in message.replies:
                # Try to get group from cache
                reply_group: beacon_message.BeaconMessageGroup = self._beacon.messages.get_group_from_message(reply)
                if not reply_group:
                    # We can't do anything with this message
                    continue

                replies.append(reply_group)

                # Get message content
                message: stoat.Message = message.channel.get_message(reply)
                if not message:
                    # Message isn't cached, we can't do anything
                    continue

                replies_content.update({reply_group.id: self._driver.sanitize_outbound(message.content)})
                replies_attachments.update({reply_group.id: len(message.attachments)})

        # Get attachments
        tasks = []

        if isinstance(message, stoat.Message):
            for attachment in message.attachments:
                tasks.append(self._get_attachment_data(attachment))

            # Get all attachments
            results = await asyncio.gather(*tasks, return_exceptions=True)
            files: list[beacon_file.BeaconFile] = [result for result in results if type(result) is beacon_file.BeaconFile]
        else:
            files: list = []

        # Assemble blocks
        blocks: dict[str, beacon_content.BeaconContentBlock] = {
            "content": text_content
        }

        embeds_index = 0
        for embed_block in embed_blocks:
            blocks.update({f'embed_{embeds_index}': embed_block})
            embeds_index += 1

        content: beacon_message.BeaconMessageContent = beacon_message.BeaconMessageContent(
            original_id=str(message.id),
            original_channel_id=str(message.channel.id),
            blocks=blocks,
            files=files,
            replies=replies,
            reply_content=replies_content,
            reply_attachments=replies_attachments
        )

        return content

    @staticmethod
    async def _get_attachment_data(attachment: stoat.Asset) -> beacon_file.BeaconFile:
        filename: str = attachment.filename
        spoiler: bool = False
        media: bool = "image/" in attachment.content_type or "video/" in attachment.content_type

        # Read data
        data: bytes = await attachment.read()

        return beacon_file.BeaconFile(
            data=data,
            url=attachment.url(),
            media=media,
            filename=filename,
            spoiler=spoiler
        )

    async def on_ready(self, _, /):
        print(f"Logged in to Stoat as {self.user.name} ({self.user.id})")

        # noinspection PyUnresolvedReferences
        self.register_driver()

    async def on_message(self, message: stoat.Message, /):
        if not self.messages_working_notif:
            self.messages_working_notif = True
            print("Bot is receiving messages from Stoat. You don't need to reboot until messages start dropping.")

        origin_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("stoat")

        # noinspection DuplicatedCode
        if message.content.startswith(self.command_prefix[0]):
            # Assume this is a text command
            return

        if message.author.id == self.user.id:
            # Do not self-bridge
            return

        # Convert message data to message.BeaconMessageContent
        content: beacon_message.BeaconMessageContent = await self._to_beacon_content(message)

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(message.server.id)

        # Convert author data to member.BeaconMember
        author: beacon_member.BeaconMember = origin_driver.get_member(server, message.author.id)

        # Convert channel data to channel.BeaconChannel
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, message.channel.id)
        if not channel:
            # We can't bridge
            return

        # Get Space
        space: beacon_space.BeaconSpace = self._beacon.spaces.get_space_for_channel(channel)
        if not space:
            # We can't bridge
            return

        # Get the ID of the webhook to use
        membership: beacon_space.BeaconSpaceMember = space.get_member(server)
        webhook_id = membership.webhook_id

        # Run preliminary checks
        preliminary_block: beacon.BeaconMessageBlockedReason | None = await self._beacon.can_send(
            author=author,
            space=space,
            content=content,
            webhook_id=webhook_id,
            skip_filter=True
        )

        # TODO: Add returning the block reason.
        if preliminary_block:
            return

        # Send message!
        await self._beacon.send(
            author=author,
            space=space,
            content=content,
            webhook_id=webhook_id
        )

    async def on_message_update(self, event: stoat.MessageUpdateEvent):
        partial_message: stoat.PartialMessage = event.message
        message: stoat.Message = partial_message.channel.get_message(partial_message.id)

        origin_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("stoat")

        # Get the BeaconMessage object for the message
        message_obj: beacon_message.BeaconMessage = self._beacon.messages.get_message(str(message.id))
        if not message_obj:
            # We can't edit messages that aren't cached
            return

        # Convert message data to message.BeaconMessageContent
        content: beacon_message.BeaconMessageContent = await self._to_beacon_content(partial_message)

        # Did we bridge this message?
        # Did we bridge this message?
        if message.masquerade and message.author_id == self.user.id:
            # We probably did
            return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.server.id))

        # Convert author data to member.BeaconMember
        author: beacon_member.BeaconMember = origin_driver.get_member(server, str(message.author.id))

        # Convert channel data to channel.BeaconChannel
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(message.channel.id))
        if not channel:
            # We can't bridge
            return

        # Get Space
        space: beacon_space.BeaconSpace = self._beacon.spaces.get_space_for_channel(channel)

        # Get the ID of the webhook to use
        membership: beacon_space.BeaconSpaceMember = space.get_member(server)
        webhook_id = membership.webhook_id

        if not space:
            # We can't bridge
            return

        # Run preliminary checks
        preliminary_block: beacon.BeaconMessageBlockedReason | None = await self._beacon.can_send(
            author=author,
            space=space,
            content=content,
            webhook_id=webhook_id,
            skip_filter=True
        )

        # TODO: Add returning the block reason.
        if preliminary_block:
            return

        # Edit the message!
        await self._beacon.edit(
            message=message_obj,
            content=content
        )

    async def on_message_delete(self, event: stoat.MessageDeleteEvent):
        message: stoat.Message = event.message

        origin_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("stoat")

        # Get the BeaconMessage object for the message
        message_obj: beacon_message.BeaconMessage = self._beacon.messages.get_message(str(message.id))
        if not message_obj:
            # We can't remove messages that aren't cached
            return

        # Did we bridge this message?
        if message.masquerade and message.author_id == self.user.id:
            # We probably did
            return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.server.id))

        # Convert channel data to channel.BeaconChannel
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(message.channel.id))
        if not channel:
            # We can't bridge
            return

        # Get Space
        space: beacon_space.BeaconSpace = self._beacon.spaces.get_space_for_channel(channel)

        if not space:
            # We can't bridge deletes, even if it was sent in the Space by the server
            return

        # Delete the message!
        await self._beacon.delete(message=message_obj)

class StoatDriverParent(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Beacon Stoat driver",
                description="Manages the Beacon driver for Stoat.",
                visible_in_help=True
            )
        )

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")
        self._driver: stoat_driver.StoatDriver | beacon_driver.BeaconDriver | None = None

        # Create stoat bot attribute
        self.stoat_bot: StoatBot | stoat_commands.Bot | None = None

        # Check if driver is already initialized
        if "stoat" in self._beacon.drivers.platforms:
            self._driver = self._beacon.drivers.get_driver("stoat")
            self.stoat_bot = self._driver.bot
            return

        # Check if we can register Stoat
        self.can_boot: bool = False
        has_whitelist: bool = self._beacon.config.get("enable_platform_whitelist")
        available_platforms: bool = self._beacon.config.get("enabled_platforms")

        if (has_whitelist and "stoat" in available_platforms) or not has_whitelist:
            self.can_boot = True

            # Reserve driver
            self._beacon.drivers.reserve_driver("stoat")

            # Create driver
            self._driver = stoat_driver.StoatDriver(self.stoat_bot, self._beacon.messages)

    async def run_stoat(self, token: str):
        if not self.can_boot:
            print("Stoat not whitelisted in Beacon config. Shutting down Stoat bot parent.")
            return

        while True:
            # noinspection PyBroadException
            try:
                bot_needs_open: bool = (self.stoat_bot is None) or (self.stoat_bot.closed if self.stoat_bot else False)
                if bot_needs_open:
                    # Create new bot
                    self.stoat_bot: StoatBot | stoat_commands.Bot = StoatBot(
                        self._beacon,
                        self._driver,
                        command_prefix=self.bot.command_prefix,
                        token=token
                    )
                    self._driver.replace_bot(self.stoat_bot)

                await self.stoat_bot.add_extensions()

                # Run bot
                # noinspection PyBroadException
                try:
                    await self.stoat_bot.start()
                except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
                    # Exit loop
                    break
                except:
                    traceback.print_exc()
                    print("stoat bot died, restarting in 5 seconds")

                    try:
                        await asyncio.sleep(5)
                    except GeneratorExit:
                        break
                else:
                    # Bot exited gracefully
                    print("Shutting down Stoat bot parent.")
                    break
            except:
                traceback.print_exc()
                print("Stoat bot parent task failed, exiting.")
                break

    @commands.Cog.listener()
    async def on_ready(self):
        # There's already a task for the bot
        if self.bot.shared_objects.get("stoat_task"):
            return

        print("Starting Stoat...")
        print("Note: Stoat/stoat.py can be problematic! If messages won't bridge, reboot the bot.")
        token: str = await self.bot.loop.run_in_executor(None, lambda: self._shinobu_secrets.retrieve("TOKEN_STOAT"))

        # Start stoat bot
        task: asyncio.Task = self.bot.loop.create_task(self.run_stoat(token))
        self.bot.shared_objects.add("stoat_task", task)

def get_cog_type():
    return StoatDriverParent

def setup(bot):
    bot.add_cog(StoatDriverParent(bot))
