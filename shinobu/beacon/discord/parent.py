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
import discord
from discord.ext import commands
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.discord import driver as discord_driver
from shinobu.beacon.models import (message as beacon_message, content as beacon_content, member as beacon_member,
                                   file as beacon_file, driver as beacon_driver, space as beacon_space,
                                   server as beacon_server, channel as beacon_channel)

class DiscordDriverParent(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Beacon Discord driver",
                description="Manages the Beacon driver for Discord.",
                visible_in_help=True
            )
        )

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")
        self._driver: discord_driver.DiscordDriver | beacon_driver.BeaconDriver | None = None

        # Check if driver is already initialized
        if "discord" in self._beacon.drivers.platforms:
            self._driver = self._beacon.drivers.get_driver("discord")
            return

        # Create driver
        self._driver = discord_driver.DiscordDriver(self.bot, self._beacon.messages, self._beacon.pairing)

        # Register driver
        self._beacon.drivers.register_driver("discord", self._driver)

    async def _to_beacon_content(self, message: discord.Message) -> beacon_message.BeaconMessageContent:
        # Create text content block
        text_content: beacon_content.BeaconContentText = beacon_content.BeaconContentText(
            content=self._driver.sanitize_outbound(message.content)
        )

        # Create embed blocks
        embed_blocks: list[beacon_content.BeaconContentEmbed] = []
        for embed in message.embeds:
            if embed.type != "rich":
                continue

            embed_block: beacon_content.BeaconContentEmbed = beacon_content.BeaconContentEmbed(
                title=embed.title,
                description=embed.description,
                url=embed.url,
                color=embed.color
            )

            if embed.author:
                embed_block.set_author(
                    text=embed.author.name,
                    url=embed.author.url,
                    icon_url=embed.author.icon_url
                )

            if embed.footer:
                embed_block.set_footer(
                    text=embed.footer.text,
                    icon_url=embed.footer.icon_url
                )

            if embed.timestamp:
                embed_block.timestamp = int(embed.timestamp.timestamp())

            for field in embed.fields:
                embed_block.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )

            # Add to embed blocks
            embed_blocks.append(embed_block)

        # Add reply if it exists
        replies: list[beacon_message.BeaconMessageGroup] = []
        reply_content: str | None = None
        reply_attachments: int = 0

        if message.reference:
            reply_group: beacon_message.BeaconMessageGroup | None = self._beacon.messages.get_group_from_message(
                str(message.reference.message_id)
            )
            if reply_group:
                replies.append(reply_group)

        if message.reference and len(replies) > 0:
            reply_message: discord.Message | None = None

            if message.reference.cached_message:
                reply_message = message.reference.cached_message
            else:
                try:
                    reply_message = await message.channel.fetch_message(message.reference.message_id)
                except discord.HTTPException:
                    pass

            if reply_message:
                uses_components_v2: bool = reply_message.flags.is_components_v2

                if uses_components_v2:
                    # Get component 300 (text display)
                    component: discord.TextDisplay | None = reply_message.get_component(300)
                    reply_content = component.content
                else:
                    reply_content = reply_message.content

                reply_attachments = len(message.attachments)

        # Get attachments
        # noinspection DuplicatedCode
        tasks = []

        for attachment in message.attachments:
            tasks.append(self._get_attachment_data(attachment))

        # Get all attachments
        results = await asyncio.gather(*tasks, return_exceptions=True)
        files: list[beacon_file.BeaconFile] = [result for result in results if type(result) is beacon_file.BeaconFile]

        # Get pin status
        is_pin: bool = message.type == discord.MessageType.pins_add

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
            original_platform="discord",
            blocks=blocks,
            files=files,
            replies=replies,
            reply_content=self._driver.sanitize_outbound(reply_content) if reply_content else None,
            reply_attachments=reply_attachments,
            message_type=beacon_message.BeaconMessageType.pins_add if is_pin else None
        )

        return content

    @staticmethod
    async def _get_attachment_data(attachment: discord.Attachment) -> beacon_file.BeaconFile:
        filename: str = attachment.filename
        spoiler: bool = attachment.is_spoiler()
        media: bool = "image/" in attachment.content_type or "video/" in attachment.content_type

        # Read data
        if media:
            try:
                data: bytes = await attachment.read(use_cached=True)
            except discord.HTTPException:
                data: bytes = await attachment.read(use_cached=False)
        else:
            data: bytes = await attachment.read(use_cached=False)

        return beacon_file.BeaconFile(
            data=data,
            url=attachment.url,
            media=media,
            filename=filename,
            spoiler=spoiler
        )

    async def handle_edit(self, message: discord.Message):
        # noinspection DuplicatedCode
        origin_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        # Get the BeaconMessage object for the message
        message_obj: beacon_message.BeaconMessage = self._beacon.messages.get_message(str(message.id))
        if not message_obj:
            # We can't edit messages that aren't cached
            return

        # Did we bridge this message?
        if message.webhook_id:
            if message_obj.author.id != str(message.webhook_id):
                # We probably did
                return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.guild.id))

        # Convert author data to member.BeaconMember
        # noinspection DuplicatedCode
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

        # Convert message data to message.BeaconMessageContent
        content: beacon_message.BeaconMessageContent = await self._to_beacon_content(message)

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
        try:
            await self._beacon.edit(
                message=message_obj,
                content=content
            )
        except beacon.BeaconPlatformDisabled:
            pass

    async def handle_delete(self, message: discord.Message):
        # noinspection DuplicatedCode
        origin_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        # Get the BeaconMessage object for the message
        message_obj: beacon_message.BeaconMessage = self._beacon.messages.get_message(str(message.id))
        if not message_obj:
            # We can't remove messages that aren't cached
            return

        # Did we bridge this message?
        if message.webhook_id:
            if message_obj.author.id != str(message.webhook_id):
                # We probably did
                return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.guild.id))

        # Convert channel data to channel.BeaconChannel
        # noinspection DuplicatedCode
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
        try:
            await self._beacon.delete(message=message_obj)
        except beacon.BeaconPlatformDisabled:
            pass

    async def handle_pin(self, message: discord.Message):
        # noinspection DuplicatedCode
        origin_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        # Get the BeaconMessage object for the message
        message_obj: beacon_message.BeaconMessage = self._beacon.messages.get_message(str(message.id))
        if not message_obj:
            # We can't pin messages that aren't cached
            return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.guild.id))

        # Convert channel data to channel.BeaconChannel
        # noinspection DuplicatedCode
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(message.channel.id))
        if not channel:
            # We can't bridge
            return

        # Get Space
        space: beacon_space.BeaconSpace = self._beacon.spaces.get_space_for_channel(channel)

        if not space:
            # We can't bridge pins, even if it was sent in the Space by the server
            return

        # Pin the message!
        try:
            await self._beacon.pin(message=message_obj, unpin=not message.pinned)
        except beacon.BeaconPlatformDisabled:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        origin_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        supported_types: list[discord.MessageType] = [
            discord.MessageType.default,
            discord.MessageType.reply,
            discord.MessageType.pins_add
        ]
        supported_types_community: list[discord.MessageType] = [
            discord.MessageType.default,
            discord.MessageType.reply
        ]

        if message.content.startswith(self.bot.command_prefix):
            # Assume this is a text command
            return

        if message.author.id == self.bot.user.id:
            # Do not self-bridge
            return

        if message.type not in supported_types:
            # Unsupported message
            return

        # noinspection DuplicatedCode
        if message.webhook_id:
            # Check if the webhook was ours (to prevent a self-bridge)
            webhook: discord.Webhook | None = origin_driver.webhooks.get_webhook(str(message.webhook_id))

            if not webhook:
                try:
                    webhook = await self.bot.fetch_webhook(message.webhook_id)
                    origin_driver.webhooks.store_webhook(str(webhook.id), webhook)
                except discord.HTTPException:
                    pass

            if webhook:
                # Does the bot own the webhook?
                if webhook.user.id == self.bot.user.id:
                    # Do not self-bridge
                    return

        # Convert guild data to server.BeaconServer
        # noinspection DuplicatedCode
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.guild.id))

        # Convert author data to member.BeaconMember
        author: beacon_member.BeaconMember | beacon_member.BeaconPartialMember | None = origin_driver.get_member(
            server, str(message.author.id)
        )

        if not author:
            # We probably could not get the author, so we create a partial member instead
            author = beacon_member.BeaconPartialMember(
                user_id=str(message.author.id),
                platform="discord",
                name=message.author.name,
                server=server,
                display_name=message.author.global_name,
                avatar_url=message.author.avatar.url if message.author.avatar else None
            )

        # Convert channel data to channel.BeaconChannel
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(message.channel.id))
        if not channel:
            # We can't bridge
            return

        # Get Space
        space: beacon_space.BeaconSpace = self._beacon.spaces.get_space_for_channel(channel)

        # noinspection DuplicatedCode
        if not space:
            # We can't bridge
            return

        # Convert message data to message.BeaconMessageContent
        content: beacon_message.BeaconMessageContent = await self._to_beacon_content(message)

        # Run preliminary checks
        preliminary_block: beacon.BeaconMessageBlockedReason | None = await self._beacon.can_send(
            author=author,
            space=space,
            content=content,
            webhook_id=str(message.webhook_id) if message.webhook_id else None,
            skip_filter=True
        )

        # TODO: Add returning the block reason.
        if preliminary_block:
            return

        # Send message!
        try:
            await self._beacon.send(
                author=author,
                space=space,
                content=content,
                webhook_id=str(message.webhook_id) if message.webhook_id else None
            )
        except beacon.BeaconPlatformDisabled:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, message: discord.Message):
        # Identify update type
        is_pin: bool = before.pinned != message.pinned

        # Check if message is pending
        if self._beacon.is_pending(str(message.id)):
            # Add callback
            if is_pin:
                self._beacon.add_callback(str(message.id), self.handle_pin, [message])
            else:
                self._beacon.add_callback(str(message.id), self.handle_edit, [message])
        else:
            # Run directly
            if is_pin:
                await self.handle_pin(message)
            else:
                await self.handle_edit(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        # Do not handle cached messages (on_message_edit does this for us)
        if payload.cached_message:
            return

        # For uncached messages, we can only handle content edits for now. This may change in a future update
        # Check if message is pending
        if self._beacon.is_pending(str(payload.new_message.id)):
            # Add callback
            self._beacon.add_callback(str(payload.new_message.id), self.handle_edit, [payload.new_message])
        else:
            # Run directly
            await self.handle_edit(payload.new_message)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # Check if message is pending
        if self._beacon.is_pending(str(message.id)):
            # Add callback
            self._beacon.add_callback(str(message.id), self.handle_delete, [message])
        else:
            # Run directly
            await self.handle_delete(message)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        # noinspection DuplicatedCode
        origin_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        to_delete: list[beacon_message.BeaconMessage] = []

        # Get messages
        for message in messages:
            # Get the BeaconMessage object for the message
            message_obj: beacon_message.BeaconMessage = self._beacon.messages.get_message(str(message.id))
            if not message_obj:
                # We can't remove messages that aren't cached
                continue

            # Did we bridge this message?
            if message.webhook_id:
                if message_obj.author.id != str(message.webhook_id):
                    # We probably did
                    continue

            to_delete.append(message_obj)

        if len(to_delete) == 0:
            # We have nothing to delete
            return

        # Convert guild data to server.BeaconServer
        # We'll use the first message as the reference
        server: beacon_server.BeaconServer = origin_driver.get_server(str(messages[0].guild.id))

        # Convert channel data to channel.BeaconChannel
        # noinspection DuplicatedCode
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(messages[0].channel.id))
        if not channel:
            # We can't bridge
            return

        # Get Space
        space: beacon_space.BeaconSpace = self._beacon.spaces.get_space_for_channel(channel)

        if not space:
            # We can't bridge deletes, even if it was sent in the Space by the server
            return

        # Delete the messages!
        try:
            await self._beacon.purge(messages=to_delete)
        except beacon.BeaconPlatformDisabled:
            pass

def get_cog_type():
    return DiscordDriverParent

def setup(bot):
    bot.add_cog(DiscordDriverParent(bot))
