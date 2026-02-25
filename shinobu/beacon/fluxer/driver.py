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

import fluxer
from shinobu.beacon.protocol import messages as beacon_messages
from shinobu.beacon.models import (driver as beacon_driver, user as beacon_user, server as beacon_server,
                                   member as beacon_member, channel as beacon_channel, message as beacon_message,
                                   messageable as beacon_messageable, content as beacon_content, file as beacon_file,
                                   webhook as beacon_webhook)

class FluxerMessageContent:
    def __init__(self, content: str | None = None, files: list[fluxer.File] | None = None,
                 embeds: list[fluxer.Embed] | None = None, replies: list[fluxer.Message] | None = None):
        self._content: str | None = content
        self._files: list[fluxer.File] = files or []
        self._embeds: list[fluxer.Embed] = embeds or []
        self._replies: list[fluxer.Message] = replies

    @property
    def content(self) -> str | None:
        return self._content

    @property
    def raw_content(self) -> str | None:
        return self._content

    @property
    def files(self) -> list[fluxer.File]:
        return self._files

    @property
    def embeds(self) -> list[fluxer.Embed]:
        return self._embeds

    @property
    def replies(self) -> list[fluxer.Message]:
        return self._replies

class FluxerBeaconContentBlockConverter:
    @staticmethod
    def text(block: beacon_content.BeaconContentText) -> str:
        """Converts a BeaconContentText to a string object."""

        return block.content

    @staticmethod
    def embed(block: beacon_content.BeaconContentEmbed) -> fluxer.Embed:
        """Converts a BeaconContentEmbed to a discord.Embed object."""

        # Create embed
        embed = fluxer.Embed(
            title=block.title,
            description=block.description,
            url=block.url,
            color=block.color,
        )

        # Set image and thumbnail data
        embed.set_image(url=block.media)
        embed.set_thumbnail(url=block.thumbnail)

        # Set author and footer data
        # noinspection DuplicatedCode
        embed.set_author(
            name=block.author["text"],
            url=block.author["url"],
            icon_url=block.author["icon_url"]
        )
        embed.set_footer(
            text=block.author["text"],
            icon_url=block.author["icon_url"]
        )

        # Add fields
        for field in block.fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field["inline"]
            )

        return embed

class FluxerBeaconFilesConverter:
    @staticmethod
    def file(file: beacon_file.BeaconFile) -> fluxer.File:
        return fluxer.File(fp=file.data, filename=file.filename, spoiler=file.spoiler)

    @staticmethod
    def files(files: list[beacon_file.BeaconFile]) -> list[fluxer.File]:
        return [fluxer.File(fp=file.data, filename=file.filename, spoiler=file.spoiler) for file in files]

class FluxerDriver(beacon_driver.BeaconDriver):
    def __init__(self, bot, message_cache: beacon_messages.BeaconMessageCache):
        super().__init__("fluxer", bot, message_cache)

        # Overwrite self.bot (to set typing)
        self._bot: fluxer.Bot | fluxer.Client = bot

        # Disable aiomultiprocess for now
        self._supports_multi = False

        # Enable age-gate
        self._supports_agegate = True
    
    def _get_guild(self, guild_id: int) -> fluxer.Guild | None:
        for guild in self.bot.guilds:
            if guild.id == guild_id:
                return guild
        
        return None

    def _to_beacon_server(self, server: fluxer.Guild) -> beacon_server.BeaconServer:
        return beacon_server.BeaconServer(
            server_id=str(server.id),
            platform=self.platform,
            name=server.name
        )

    def _to_beacon_channel(self, channel: fluxer.Channel) -> beacon_channel.BeaconChannel:
        server = self.get_server(str(channel.guild_id))

        return beacon_channel.BeaconChannel(
            channel_id=str(channel.id),
            platform=self.platform,
            name=channel.name,
            server=server,
            nsfw=channel.nsfw
        )

    def _to_beacon_user(self, user: fluxer.User) -> beacon_user.BeaconUser:
        return beacon_user.BeaconUser(
            user_id=str(user.id),
            platform=self.platform,
            name=user.username,
            display_name=user.global_name,
            avatar_url=user.avatar_url
        )

    def _to_beacon_member(self, member: fluxer.GuildMember, server: fluxer.Guild) -> beacon_member.BeaconMember:
        # Because fluxer.py doesn't add a way to get a member's server ID,
        # we'll need to process it separately
        server = self._to_beacon_server(server)

        return beacon_member.BeaconMember(
            user_id=str(member.user.id),
            platform=self.platform,
            name=member.user.username,
            server=server,
            display_name=member.user.global_name,
            avatar_url=member.user.avatar_url
        )

    def _to_beacon_message(self, message: fluxer.Message) -> beacon_message.BeaconMessage:
        server = self.get_server(str(message.guild_id))
        author = self._to_beacon_user(message.author)
        channel = self._to_beacon_channel(message.channel)

        # Convert replies to Beacon messages
        # fluxer.py doesb't provide this for some reason??
        replies = []

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

    def _to_beacon_webhook(self, webhook: fluxer.Webhook) -> beacon_webhook.BeaconWebhook:
        server = self.get_server(str(webhook.guild_id))
        channel = self.get_channel(server, str(webhook.channel_id))

        return beacon_webhook.BeaconWebhook(
            webhook_id=str(webhook.id),
            platform=self.platform,
            server=server,
            channel=channel
        )

    async def _to_fluxer_content(self, content: beacon_message.BeaconMessageContent,
                                 _: beacon_messageable.BeaconMessageable) -> FluxerMessageContent:
        # Content
        embeds: list[fluxer.Embed] = []
        replies: list[fluxer.Message] = []
        # noinspection DuplicatedCode
        text_components: list[str] = []
        files: list[fluxer.File] = FluxerBeaconFilesConverter.files(content.files)

        # Convert blocks
        for block_id in content.blocks:
            block_obj: beacon_content.BeaconContentBlock = content.blocks[block_id]

            if isinstance(block_obj, beacon_content.BeaconContentText):
                text_components.append(FluxerBeaconContentBlockConverter.text(block_obj))
            elif isinstance(block_obj, beacon_content.BeaconContentEmbed):
                embeds.append(FluxerBeaconContentBlockConverter.embed(block_obj))

        # Replies will be implemented once fluxer.py has replies built in

        # Assemble to FluxerMessageContent
        return FluxerMessageContent(
            content=self.sanitize_inbound("\n".join(text_components)),
            files=files,
            embeds=embeds,
            replies=replies
        )

    # noinspection DuplicatedCode
    def sanitize_outbound(self, content: str) -> str:
        user_mentions = [item.split('>')[0] for item in content.split("<@")] if len(content.split("<@")) > 1 else []
        channel_mentions = [item.split('>')[0] for item in content.split("<#")] if len(content.split("<#")) > 1 else []

        for user_mention in user_mentions:
            # Check if this is a role mention
            if user_mention.startswith('&'):
                continue

            try:
                user = self.bot.get_user(int(user_mention))
            except ValueError:
                # This is not a valid snowflake
                continue

            if not user:
                # This is not a valid user
                continue

            content = content.replace(f"<@{user_mention}>", f"@{user.display_name or user.name}")

        for channel_mention in channel_mentions:
            try:
                channel = self.bot.get_channel(int(channel_mention))
            except ValueError:
                # This is not a valid snowflake
                continue

            if not channel:
                # This is not a valid channel
                continue

            content = content.replace(f"<#{channel_mention}>", f"#{channel.name}")

        return content

    def sanitize_inbound(self, content: str) -> str:
        # Escape pings
        return content.replace(
            "@everyone", "@ everyone"
        ).replace(
            "@here", "@ here"
        ).replace(
            "<@", "<\\@"
        ).replace(
            "<@&", "<\\@\\&"
        )

    # Beacon driver functions
    def get_user(self, user_id: str):
        user = self.bot.get_user(int(user_id))

        if not user:
            return None

        return self._to_beacon_user(user)

    async def fetch_user(self, user_id: str):
        user = await self.bot.fetch_user(user_id)

        return self._to_beacon_user(user)

    def _get_member(self, server: beacon_server.BeaconServer, member_id: str):
        fluxer_server = self.bot.get_guild(int(server.id))

        if not fluxer_server:
            return None

        member = fluxer_server.get_member(int(member_id))

        if not member:
            return None

        return self._to_beacon_member(member, fluxer_server)

    def _get_channel(self, server: beacon_server.BeaconServer, channel_id: str):
        fluxer_server = self.bot.get_guild(int(server.id))

        if not fluxer_server:
            return None

        channel = fluxer_server.get_channel(int(channel_id))

        if not channel:
            return None

        return self._to_beacon_channel(channel)

    def get_server(self, server_id: str):
        server = self.bot.get_guild(int(server_id))

        if not server:
            return None

        return self._to_beacon_server(server)

    async def fetch_server(self, server_id: str):
        server = await self.bot.fetch_guild(server_id)

        return self._to_beacon_server(server)

    def get_webhook(self, webhook_id: str):
        webhook = self._webhooks.get_webhook(webhook_id)

        if not webhook:
            return None

        return self._to_beacon_webhook(webhook)

    async def fetch_webhook(self, webhook_id: str):
        webhook = await self.bot.fetch_webhook(int(webhook_id))

        # Store webhook to cache
        self._webhooks.store_webhook(str(webhook.id), webhook)

        return self._to_beacon_webhook(webhook)

    # noinspection DuplicatedCode
    async def send(self, destination: beacon_messageable.BeaconMessageable,
                   content: beacon_message.BeaconMessageContent, send_as: beacon_user.BeaconUser | None = None,
                   webhook_id: str | None = None, self_send: bool = False):
        # Get message options
        send_as_webhook: bool = webhook_id is not None
        send_as_user: bool = send_as is not None

        # Run sanity checks
        if send_as_user and not send_as_webhook:
            raise ValueError("A webhook is needed to set a per-message name and avatar")

        # Get webhook (if needed)
        webhook_obj: fluxer.Webhook | None = None
        if send_as_webhook:
            # Ensure webhook is in cache
            await self.getch_webhook(webhook_id)

            # Get webhook from cache
            webhook_obj = self._webhooks.get_webhook(webhook_id)

        # Get user name and avatar
        custom_name: str | None = None
        custom_avatar: str | None = None
        if send_as_user:
            custom_name = send_as.display_name
            custom_avatar = send_as.avatar_url

        # Convert message content data
        fluxer_content: FluxerMessageContent = await self._to_fluxer_content(
            content, destination
        )

        # Convert bot user to BeaconUser
        self_user = self.get_user(str(self.bot.user.id))

        # Get target
        if webhook_id:
            target_channel_id: str = str(webhook_obj.channel_id)
        else:
            target_channel_id: str = destination.id

        target = self.bot.get_channel(int(target_channel_id))

        server: beacon_server.BeaconServer = self.get_server(str(target.guild_id))
        if not server:
            # Server is not cached here!
            return

        # Convert channel to BeaconChannel
        channel: beacon_channel.BeaconChannel = self.get_channel(server, str(target.id))

        # Are we self-sending?
        if target_channel_id == content.original_channel_id and not self_send:
            # Return message object but don't send

            return beacon_message.BeaconMessage(
                message_id=content.original_id,
                platform=self.platform,
                author=send_as or self_user,
                server=self.get_server(str(target.guild_id)),
                channel=channel,
                content=fluxer_content.raw_content,
                attachments=len(fluxer_content.files),
                replies=[reply.get_message_for(channel) for reply in content.replies] if channel else [],
                webhook_id=webhook_id if webhook_obj else None
            )

        # Send the message!
        if webhook_id:
            if not target:
                return None

            message = await webhook_obj.send(
                content=fluxer_content.content,
                embeds=fluxer_content.embeds,
                files=fluxer_content.files,
                username=custom_name,
                avatar_url=custom_avatar,
                wait=True
            )
        else:
            if not target:
                return None

            message = await target.send(
                content=fluxer_content.content,
                embeds=fluxer_content.embeds,
                files=fluxer_content.files
            )

        return beacon_message.BeaconMessage(
            message_id=str(message.id),
            platform=self.platform,
            author=send_as or self_user,
            server=self.get_server(str(target.guild_id)),
            channel=channel,
            content=fluxer_content.raw_content,
            attachments=len(fluxer_content.files),
            replies=[reply.get_message_for(channel) for reply in content.replies] if channel else [],
            webhook_id=webhook_id if webhook_obj else None
        )

    async def _delete(self, message: beacon_message.BeaconMessage):
        channel = self.bot.get_channel(int(message.channel.id))
        message_obj = await channel.fetch_message(int(message.id))

        # Delete message
        await message_obj.delete()
