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
        self.beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")

        # Check if driver is already initialized
        if "discord" in self.beacon.drivers.platforms:
            return

        # Register driver
        self.beacon.drivers.register_driver("discord", discord_driver.DiscordDriver(
            self.bot, self.beacon.messages
        ))

    async def _to_beacon_content(self, message: discord.Message) -> beacon_message.BeaconMessageContent:
        # Create text content block
        text_content: beacon_content.BeaconContentText = beacon_content.BeaconContentText(
            content=message.content
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

            if embed.author:
                embed_block.set_author(
                    text=embed.author.name,
                    url=embed.author.url,
                    icon_url=embed.author.icon_url
                )

            if embed.footer:
                embed_block.set_footer(
                    text=embed.footer.text,
                    icon_url=embed.author.icon_url
                )

            if embed.timestamp:
                embed.timestamp = int(embed.timestamp.timestamp())

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
        if message.reference:
            reply_group: beacon_message.BeaconMessageGroup = self._beacon.messages.get_group_from_message(
                str(message.reference.message_id)
            )

            # If the message is cached, overwrite its content
            # If the Discord message object isn't cached, the driver can fetch that for us later
            reply_message: beacon_message.BeaconMessage | None = self._beacon.messages.get_message(
                str(message.reference.message_id)
            )
            if reply_message and message.reference.cached_message:
                uses_components_v2: bool = discord.MessageFlags.is_components_v2 in message.reference.cached_message.flags

                if uses_components_v2:
                    # Get component 300 (text display)
                    component: discord.TextDisplay | None = message.reference.cached_message.get_component(300)
                    if component:
                        reply_message.edit_content(component.content)
                else:
                    reply_message.edit_content(message.content)

        # Get attachments
        tasks = []

        for attachment in message.attachments:
            tasks.append(self._get_attachment_data(attachment))

        # Get all attachments
        results = await asyncio.gather(*tasks, return_exceptions=True)
        files: list[beacon_file.BeaconFile] = [result for result in results if type(result) is beacon_file.BeaconFile]

        # Assemble blocks
        blocks: dict[str, beacon_content.BeaconContentBlock] = {
            "content": text_content
        }

        embeds_index = 0
        for embed_block in embed_blocks:
            blocks.update({f'embed_{embeds_index}': embed_block})
            embeds_index += 1

        content: beacon_message.BeaconMessageContent = beacon_message.BeaconMessageContent(
            blocks=blocks,
            files=files,
            replies=replies
        )

        return content

    @staticmethod
    async def _get_attachment_data(attachment: discord.Attachment) -> beacon_file.BeaconFile:
        data: bytes = await attachment.read(use_cached=True)
        filename: str = attachment.filename
        spoiler: bool = attachment.is_spoiler()

        return beacon_file.BeaconFile(
            data=data,
            filename=filename,
            spoiler=spoiler
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        origin_driver: beacon_driver.BeaconDriver = self.beacon.drivers.get_driver("discord")

        if message.author.id == self.bot.user.id:
            # Do not self-bridge
            return

        if message.webhook_id:
            # Check if the webhook was ours (to prevent a self-bridge)
            webhook: discord.Webhook | None = origin_driver.webhooks.get_webhook(str(message.webhook_id))

            if not webhook:
                try:
                    webhook = await self.bot.fetch_webhook(message.webhook_id)
                except discord.HTTPException:
                    pass

            if webhook:
                # Does the bot own the webhook?
                if webhook.user.id == self.bot.user.id:
                    # Do not self-bridge
                    return

        # Convert message data to message.BeaconMessageContent
        content: beacon_message.BeaconMessageContent = await self._to_beacon_content(message)

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.guild.id))

        # Convert author data to member.BeaconMember
        author: beacon_member.BeaconMember = origin_driver.get_member(server, str(message.author.id))

        # Convert channel data to channel.BeaconChannel
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(message.channel.id))

        # Get Space
        space: beacon_space.BeaconSpace = self.beacon.spaces.get_space_for_channel(channel)

        if not space:
            # We can't bridge
            return

        # Run preliminary checks
        preliminary_block: beacon.BeaconMessageBlockedReason | None = await self.beacon.can_send(
            author=author,
            space=space,
            content=content,
            webhook_id=str(message.webhook_id),
            skip_filter=True
        )

        if preliminary_block:
            return

        # Send message!
        await self.beacon.send(
            author=author,
            space=space,
            content=content
        )

def get_cog_type():
    return DiscordDriverParent

def setup(bot):
    bot.add_cog(DiscordDriverParent(bot))
