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

import stoat
from stoat.ext import commands
from shinobu.beacon.protocol import messages as beacon_messages
from shinobu.beacon.models import (driver as beacon_driver, user as beacon_user, server as beacon_server,
                                   member as beacon_member, channel as beacon_channel, message as beacon_message,
                                   messageable as beacon_messageable, content as beacon_content, file as beacon_file)
from shinobu.beacon.stoat.models import embed as stoat_embed

class StoatMessageContent:
    def __init__(self, content: str | None = None, files: list[stoat.ResolvableResource] | None = None,
                 embeds: list[stoat_embed.Embed] | None = None,
                 replies: list[stoat.Message | stoat.Reply] | None = None):
        self._content: str | None = content
        self._files: list[stoat.ResolvableResource] = files or []
        self._embeds: list[stoat_embed.Embed] = embeds or []
        self._replies: list[stoat.Message | stoat.Reply] = replies

    @property
    def content(self) -> str | None:
        return self._content

    @property
    def raw_content(self) -> str | None:
        return self._content

    @property
    def files(self) -> list[stoat.ResolvableResource]:
        return self._files

    @property
    def embeds(self) -> list[stoat_embed.Embed]:
        return self._embeds

    @property
    def replies(self) -> list[stoat.Message | stoat.Reply]:
        return self._replies

class StoatBeaconContentBlockConverter:
    @staticmethod
    def text(block: beacon_content.BeaconContentText) -> str:
        """Converts a BeaconContentText to a string object."""

        return block.content

    @staticmethod
    def embed(block: beacon_content.BeaconContentEmbed) -> stoat_embed.Embed:
        """Converts a BeaconContentEmbed to a discord.Embed object."""

        # Create embed
        embed = stoat_embed.Embed(
            title=block.title,
            description=block.description,
            url=block.url,
            color=block.color,
            media=block.media,
            icon_url=block.author["icon_url"]
        )

        # Add fields
        for field in block.fields:
            embed.add_field(
                name=field["name"],
                value=field["value"]
            )

        return embed

class StoatBeaconFilesConverter:
    @staticmethod
    def file(file: beacon_file.BeaconFile) -> stoat.ResolvableResource:
        return file.data

    @staticmethod
    def files(files: list[beacon_file.BeaconFile]) -> list[stoat.ResolvableResource]:
        return [file.data for file in files]

class StoatDriver(beacon_driver.BeaconDriver):
    def __init__(self, bot, message_cache: beacon_messages.BeaconMessageCache):
        super().__init__("stoat", bot, message_cache)

        # Overwrite self.bot (to set typing)
        self._bot: commands.Bot = bot

        # Enable age-gate
        self._supports_agegate = True

    def _to_beacon_server(self, server: stoat.Server) -> beacon_server.BeaconServer:
        return beacon_server.BeaconServer(
            server_id=str(server.id),
            platform=self.platform,
            name=server.name
        )

    def _to_beacon_channel(self, channel: stoat.ServerChannel) -> beacon_channel.BeaconChannel:
        server = self._to_beacon_server(channel.server)

        return beacon_channel.BeaconChannel(
            channel_id=str(channel.id),
            platform=self.platform,
            name=channel.name,
            server=server,
            nsfw=channel.nsfw
        )

    def _to_beacon_user(self, user: stoat.User) -> beacon_user.BeaconUser:
        return beacon_user.BeaconUser(
            user_id=str(user.id),
            platform=self.platform,
            name=user.name,
            display_name=user.display_name,
            avatar_url=user.avatar.url() if user.avatar else None
        )

    def _to_beacon_member(self, member: stoat.Member) -> beacon_member.BeaconMember:
        server = self._to_beacon_server(self.bot.get_server(member.server_id))

        return beacon_member.BeaconMember(
            user_id=str(member.id),
            platform=self.platform,
            name=member.name,
            server=server,
            display_name=member.display_name,
            avatar_url=member.avatar.url() if member.avatar else None
        )

    def _to_beacon_message(self, message: stoat.Message) -> beacon_message.BeaconMessage:
        author = self._to_beacon_member(message.author)
        server = self._to_beacon_server(message.server)
        channel = self._to_beacon_channel(message.channel)

        # Convert replies to Beacon messages
        replies = [self._messages.get_message(reply) for reply in message.replies]

        return beacon_message.BeaconMessage(
            message_id=str(message.id),
            platform=self.platform,
            author=author,
            server=server,
            channel=channel,
            content=message.content,
            attachments=len(message.attachments),
            replies=replies,
            webhook_id=None
        )

    @staticmethod
    async def _to_stoat_content(content: beacon_message.BeaconMessageContent,
                                destination: beacon_messageable.BeaconMessageable) -> StoatMessageContent:
        # Content
        embeds: list[stoat_embed.Embed] = []
        replies: list[stoat.Message | stoat.Reply] = []
        text_components: list[str] = []
        files: list[stoat.ResolvableResource] = StoatBeaconFilesConverter.files(content.files)

        # Convert blocks
        for block_id in content.blocks:
            block_obj: beacon_content.BeaconContentBlock = content.blocks[block_id]

            if isinstance(block_obj, beacon_content.BeaconContentText):
                text_components.append(StoatBeaconContentBlockConverter.text(block_obj))
            elif isinstance(block_obj, beacon_content.BeaconContentEmbed):
                embeds.append(StoatBeaconContentBlockConverter.embed(block_obj))

        # Process reply
        for reply_message_group in content.replies:
            # Find channel-specific reply
            reply_message: beacon_message.BeaconMessage | None = reply_message_group.get_message_for(destination)

            if not reply_message:
                continue

            # We only need the reply ID
            reply_id: str = reply_message.id

            # Create reply object
            reply_obj: stoat.Reply = stoat.Reply(reply_id)

            # Add to replies
            replies.append(reply_obj)

        # Assemble to StoatMessageContent
        return StoatMessageContent(
            content="\n".join(text_components),
            files=files,
            embeds=embeds,
            replies=replies
        )

    def sanitize_outbound(self, content: str) -> str:
        # noinspection DuplicatedCode
        user_mentions = [item.split('>')[0] for item in content.split("<@")] if len(content.split("<@")) > 1 else []
        channel_mentions = [item.split('>')[0] for item in content.split("<#")] if len(content.split("<#")) > 1 else []
        emoji_mentions = [
                             item.split('>')[0].split(':')[1] for item in content.split("<:")
                         ] if len(content.split("<:")) > 1 else [] + [
                             item.split('>')[0].split(':')[1] for item in content.split("<a:")
                         ] if len(content.split("<a:")) > 1 else []

        for user_mention in user_mentions:
            # Check if this is a role mention
            if user_mention.startswith('&'):
                continue

            user = self.bot.get_user(user_mention)
            if not user:
                # This is not a valid user
                continue

            content = content.replace(f"<@{user_mention}>", f"@{user.display_name or user.name}")

        for channel_mention in channel_mentions:
            channel = self.bot.get_channel(channel_mention)
            if not channel:
                # This is not a valid channel
                continue

            content = content.replace(f"<#{channel_mention}>", f"#{channel.name}")

        for emoji_mention in emoji_mentions:
            emoji = self.bot.get_emoji(emoji_mention)
            if not emoji:
                # This is not a valid emoji
                continue

            content = content.replace(
                f"<a:{emoji.name}:{emoji_mention}>" if emoji.animated else f"<:{emoji.name}:{emoji_mention}>",
                f":{emoji.name}:"
            )

        return content

    def sanitize_inbound(self, content: str) -> str:
        """Nothing to sanitize"""
        return content

    # Beacon driver functions
    def get_user(self, user_id: str):
        user = self.bot.get_user(user_id)

        if not user:
            return None

        return self._to_beacon_user(user)

    async def fetch_user(self, user_id: str):
        user = await self.bot.fetch_user(user_id)

        return self._to_beacon_user(user)

    def _get_member(self, server: beacon_server.BeaconServer, member_id: str):
        stoat_server = self.bot.get_server(server.id)

        if not stoat_server:
            return None

        member = stoat_server.get_member(member_id)

        if not member:
            return None

        return self._to_beacon_member(member)

    def _get_channel(self, server: beacon_server.BeaconServer, channel_id: str):
        stoat_server = self.bot.get_server(server.id)

        if not stoat_server:
            return None

        channel = stoat_server.get_channel(channel_id)

        if not channel:
            return None

        return self._to_beacon_channel(channel)

    def get_server(self, server_id: str):
        server = self.bot.get_server(server_id)

        if not server:
            return None

        return self._to_beacon_server(server)

    async def fetch_server(self, server_id: str):
        server = await self.bot.fetch_server(server_id)

        return self._to_beacon_server(server)

    async def send(self, destination: beacon_messageable.BeaconMessageable,
                   content: beacon_message.BeaconMessageContent, send_as: beacon_user.BeaconUser | None = None,
                   webhook_id: str | None = None, self_send: bool = False):
        # Get message options
        send_as_user: bool = send_as is not None

        # Get user name and avatar
        # noinspection DuplicatedCode
        custom_name: str | None = None
        custom_avatar: str | None = None
        if send_as_user:
            custom_name = send_as.display_name
            custom_avatar = send_as.avatar_url

        # Convert message content data
        stoat_content: StoatMessageContent = await self._to_stoat_content(content, destination)

        # Convert bot user to BeaconUser
        self_user = self.get_user(self.bot.user.id)

        # Get target
        target: stoat.ServerChannel = self.bot.get_channel(destination.id)

        # Convert channel to BeaconChannel
        channel: beacon_channel.BeaconChannel = self.get_channel(self.get_server(target.server.id), target.id)

        # Are we self-sending?
        # noinspection DuplicatedCode
        if target.id == content.original_channel_id and not self_send:
            # Return message object but don't send
            return beacon_message.BeaconMessage(
                message_id=content.original_id,
                platform=self.platform,
                author=send_as or self_user,
                server=self.get_server(target.server.id),
                channel=channel,
                content=stoat_content.content,
                attachments=len(stoat_content.files),
                replies=[reply.get_message_for(channel) for reply in content.replies] if channel else [],
                webhook_id=None
            )

        # Send the message!
        masquerade: stoat.MessageMasquerade | None = None
        if custom_name:
            masquerade = stoat.MessageMasquerade(
                name=custom_name,
                avatar=custom_avatar
            )

        message = await target.send(
            content=stoat_content.content,
            embeds=stoat_content.embeds,
            attachments=stoat_content.files,
            masquerade=masquerade
        )

        # noinspection DuplicatedCode
        return beacon_message.BeaconMessage(
            message_id=message.id,
            platform=self.platform,
            author=send_as or self_user,
            server=self.get_server(target.server.id),
            channel=channel,
            content=stoat_content.content,
            attachments=len(stoat_content.files),
            replies=[reply.get_message_for(channel) for reply in content.replies] if channel else [],
            webhook_id=None
        )

    async def _edit(self, message: beacon_message.BeaconMessage, content: beacon_message.BeaconMessageContent):
        channel = self.bot.get_channel(message.channel.id)
        message_obj = await channel.fetch_message(message.id)

        # Convert message content data
        stoat_content: StoatMessageContent = await self._to_stoat_content(content, destination=message.channel)

        # Edit message
        await message_obj.edit(
            content=stoat_content.content,
            embeds=stoat_content.embeds
        )

    async def _delete(self, message: beacon_message.BeaconMessage):
        channel = self.bot.get_channel(message.channel.id)
        message_obj = await channel.fetch_message(message.id)

        # Delete message
        await message_obj.delete()
