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

import io
import discord
from datetime import datetime
from discord.ext import bridge
from shinobu.beacon.protocol import messages as beacon_messages
from shinobu.beacon.models import (driver as beacon_driver, user as beacon_user, server as beacon_server,
                                   member as beacon_member, channel as beacon_channel, webhook as beacon_webhook,
                                   message as beacon_message, messageable as beacon_messageable,
                                   content as beacon_content, file as beacon_file)

class DiscordMessageContent:
    def __init__(self, content: str | None = None, components: discord.ui.DesignerView | discord.ui.View | None = None,
                 files: list[discord.File] | None = None, embeds: list[discord.Embed] | None = None):
        self._content: str | None = content
        self._components: discord.ui.DesignerView | discord.ui.View | None = components
        self._files: list[discord.File] = files or []
        self._embeds: list[discord.Embed] = embeds or []
        self._components_v2: bool = (
                type(components) is discord.ui.DesignerView and components.is_components_v2()
        ) if components else False

    @property
    def content(self) -> str | None:
        if self._components_v2:
            return None

        return self._content

    @property
    def raw_content(self) -> str | None:
        return self._content

    @property
    def components(self) -> discord.ui.DesignerView | discord.ui.View | None:
        return self._components

    @property
    def files(self) -> list[discord.File]:
        return self._files

    @property
    def embeds(self) -> list[discord.Embed]:
        if self._components_v2:
            return []

        return self._embeds

class DiscordBeaconContentBlockConverter:
    @staticmethod
    def text(block: beacon_content.BeaconContentText) -> str:
        """Converts a BeaconContentText to a string object."""

        return block.content

    @staticmethod
    def embed(block: beacon_content.BeaconContentEmbed) -> discord.Embed:
        """Converts a BeaconContentEmbed to a discord.Embed object."""

        # Create embed
        embed = discord.Embed(
            title=block.title,
            description=block.description,
            timestamp=datetime.fromtimestamp(block.timestamp),
            url=block.url,
            color=block.color,
            image=block.media,
            thumbnail=block.thumbnail
        )

        # Set author and footer data
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

    @staticmethod
    def embed_container(block: beacon_content.BeaconContentEmbed) -> discord.ui.Container:
        """Converts a BeaconContentEmbed to a discord.ui.Container object."""

        # Create container
        container = discord.ui.Container(
            color=block.color,
        )

        # Add author/header
        author_content = block.author['text']

        if block.author['url']:
            author_content = f"[{block.author['text']}]({block.author['url']})"

        if block.author['text']:
            container.add_text(author_content)

        # Add title and description block
        title_desc_content = f"## {block.title}\n{block.description}"

        if block.url:
            title_desc_content = f"## [{block.title}]({block.url})\n{block.description}"

        if not block.title:
            title_desc_content = block.description

        if title_desc_content:
            title_thumbnail_section = discord.ui.Section()
            title_thumbnail_section.add_text(title_desc_content)

            # Add thumbnail
            if block.thumbnail:
                title_thumbnail_section.set_accessory(discord.ui.Thumbnail(block.thumbnail))

            container.add_item(title_thumbnail_section)

        # Add fields
        current_section = discord.ui.Section()
        for field in block.fields:
            field_components = []

            if field["name"]:
                field_components.append(f"### {field['name']}")
            if field["value"]:
                field_components.append(field["value"])

            current_section.add_text("\n".join(field_components))

            if not field["inline"] or len(current_section.items) == 3:
                container.add_item(current_section)
                current_section = discord.ui.Section()

        # Ensure all rows have been added
        if len(current_section.items) > 0:
            container.add_item(current_section)

        # Add media
        if block.media:
            container.add_file(block.media)

        # Add footer
        footer_components = []

        if block.footer["text"]:
            footer_components.append(block.footer["text"])
        if block.timestamp:
            footer_components.append(f"<t:{round(block.timestamp)}:f>")

        if len(footer_components) > 0:
            container.add_item(discord.ui.TextDisplay(" • ".join(footer_components)))

        return container

class DiscordBeaconFilesConverter:
    @staticmethod
    def file(file: beacon_file.BeaconFile) -> discord.File:
        return discord.File(fp=io.BytesIO(file.data), filename=file.filename, spoiler=file.spoiler)

    @staticmethod
    def files(files: list[beacon_file.BeaconFile]) -> list[discord.File]:
        return [discord.File(fp=io.BytesIO(file.data), filename=file.filename, spoiler=file.spoiler) for file in files]

class DiscordDriver(beacon_driver.BeaconDriver):
    def __init__(self, bot, message_cache: beacon_messages.BeaconMessageCache):
        super().__init__("discord", bot, message_cache)

        # Overwrite self.bot (to set typing)
        self.bot: bridge.Bot = bot

        # Enable age-gate
        self._supports_agegate = True

        # Components v2 flag
        self._use_components_v2: bool = True

    def _to_beacon_server(self, guild: discord.Guild) -> beacon_server.BeaconServer:
        return beacon_server.BeaconServer(
            server_id=str(guild.id),
            platform=self.platform,
            name=guild.name,
            filesize_limit=guild.filesize_limit
        )

    def _to_beacon_channel(self, channel: discord.TextChannel) -> beacon_channel.BeaconChannel:
        server = self._to_beacon_server(channel.guild)

        return beacon_channel.BeaconChannel(
            channel_id=str(channel.id),
            platform=self.platform,
            name=channel.name,
            server=server,
            nsfw=channel.nsfw
        )

    def _to_beacon_user(self, user: discord.User) -> beacon_user.BeaconUser:
        return beacon_user.BeaconUser(
            user_id=str(user.id),
            platform=self.platform,
            name=user.name,
            display_name=user.display_name,
            avatar_url=user.avatar.url if user.avatar else None
        )

    def _to_beacon_member(self, member: discord.Member) -> beacon_member.BeaconMember:
        server = self._to_beacon_server(member.guild)

        return beacon_member.BeaconMember(
            user_id=str(member.id),
            platform=self.platform,
            name=member.name,
            server=server,
            display_name=member.display_name,
            avatar_url=member.avatar.url if member.avatar else None
        )

    def _to_beacon_message(self, message: discord.Message) -> beacon_message.BeaconMessage:
        author = self._to_beacon_member(message.author)
        server = self._to_beacon_server(message.guild)
        channel = self._to_beacon_channel(message.channel)

        # Convert replies to Beacon messages
        replies = [self._messages.get_message(str(message.reference.message_id))]

        return beacon_message.BeaconMessage(
            message_id=str(message.id),
            platform=self.platform,
            author=author,
            server=server,
            channel=channel,
            content=message.content,
            attachments=len(message.attachments),
            replies=replies,
            webhook_id=str(message.webhook_id) if message.webhook_id else None
        )

    def _to_beacon_webhook(self, webhook: discord.Webhook) -> beacon_webhook.BeaconWebhook:
        server = self._to_beacon_server(webhook.guild)
        channel = self._to_beacon_channel(webhook.channel)

        return beacon_webhook.BeaconWebhook(
            webhook_id=str(webhook.id),
            platform=self.platform,
            server=server,
            channel=channel
        )

    async def _to_discord_content(self, content: beacon_message.BeaconMessageContent,
                                  destination: beacon_messageable.BeaconMessageable, use_components_v2: bool | None = None
                                  ) -> DiscordMessageContent:
        if use_components_v2 is None:
            use_components_v2 = self._use_components_v2

        # Components v2 content
        container_blocks: list[discord.ui.Container] = []
        reply_blocks: list[discord.ui.Container] = []

        # Legacy content
        legacy_embeds: list[discord.Embed] = []
        legacy_reply_components = discord.ui.View(store=False)

        # Universal content
        text_components: list[str] = []
        files: list[discord.File] = DiscordBeaconFilesConverter.files(content.files)

        # Convert blocks
        for block_id in content.blocks:
            block_obj: beacon_content.BeaconContentBlock = content.blocks[block_id]

            if isinstance(block_obj, beacon_content.BeaconContentText):
                text_components.append(DiscordBeaconContentBlockConverter.text(block_obj))
            elif isinstance(block_obj, beacon_content.BeaconContentEmbed):
                container_blocks.append(DiscordBeaconContentBlockConverter.embed_container(block_obj))
                legacy_embeds.append(DiscordBeaconContentBlockConverter.embed(block_obj))

        # Process reply
        for reply_message_group in content.replies:
            # Find channel-specific reply
            reply_message: beacon_message.BeaconMessage | None = reply_message_group.get_message_for(destination)

            if not reply_message:
                continue

            reply_author: str = f"{reply_message.author.display_name if reply_message.author else '[unknown]'}"
            reply_url: str = f"https://discord.com/channels/{reply_message.server.id}/{reply_message.channel.id}/{reply_message.id}"
            reply_content: str | None = None

            # Get message content
            if content.reply_content:
                reply_content = content.reply_content
            else:
                # Fetch message
                channel = self.bot.get_channel(int(reply_message.channel.id))

                try:
                    message = await channel.fetch_message(int(reply_message.id))
                except discord.HTTPException:
                    pass
                else:
                    if discord.MessageFlags.is_components_v2 in message.flags:
                        # Get component with ID 300 (this is our text component)
                        message_text_block: discord.Component = message.get_component(300)

                        # Is the component a text block as expected?
                        if isinstance(message_text_block, discord.TextDisplay):
                            reply_content = message_text_block.content

            # Create reply container (will get ID 10X)
            reply_container: discord.ui.Container = discord.ui.Container()

            # Create reply jump button
            # noinspection PyTypeChecker
            reply_button: discord.ui.Button = discord.ui.Button(
                style=discord.ButtonStyle.link,
                label=f'Jump to message',
                url=reply_url
            )

            reply_text: discord.ui.TextDisplay = discord.ui.TextDisplay(
                f"\U000021AA\U0000FE0F **Replying to @{reply_author}**"
            )

            # Create content text display (if possible)
            if reply_content:
                # We'll cap content to 200 characters
                if len(reply_content) > 200:
                    reply_content = reply_content[:197] + "..."

                reply_text= discord.ui.TextDisplay(
                    f"\U000021AA\U0000FE0F **Replying to @{reply_author}** - {reply_content}"
                )
            elif content.reply_attachments > 0:
                reply_text = discord.ui.TextDisplay(
                    f"\U000021AA\U0000FE0F **Replying to @{reply_author}** \U0001F5BC\U0000FE0F"
                )

            # Create reply action row
            reply_section: discord.ui.Section = discord.ui.Section(
                reply_text, accessory=reply_button
            )
            reply_container.add_item(reply_section)
            reply_blocks.append(reply_container)

            # Add button to legacy reply components
            available_trimmed_space = 80 - len(f'Replying to @{reply_author} - ')
            reply_content_trimmed = reply_content
            if len(reply_content) > available_trimmed_space:
                reply_content_trimmed = reply_content[:(available_trimmed_space - 3)] + "..."

            # noinspection PyTypeChecker
            legacy_reply_components.add_item(discord.ui.ActionRow(
                discord.ui.Button(
                    style=discord.ButtonStyle.link,
                    label=f'Replying to @{reply_author} - {reply_content_trimmed}',
                    emoji='\U000021AA\U0000FE0F',
                    url=reply_url
                )
            ))

        # Assemble to DiscordMessageContent
        if use_components_v2:
            # Assemble components
            components = discord.ui.DesignerView(
                store=False
            )

            # Add replies display (we will assign ID 1XX to these)
            current_reply_id = 100
            for reply_block in reply_blocks:
                reply_block.id = current_reply_id
                components.add_item(reply_block)
                current_reply_id += 1

            # Add text display (we will assign ID 300 to this)
            components.add_item(discord.ui.TextDisplay(
                "\n".join(text_components),
                id=300
            ))

            # Add containers (we will assign 4XX to these)
            current_container_id = 400
            for container_block in container_blocks:
                container_block.id = current_container_id
                components.add_item(container_block)
                current_container_id += 1

            return DiscordMessageContent(
                content="\n".join(text_components),
                components=components,
                files=files
            )
        else:
            # Use Components v1
            return DiscordMessageContent(
                content="\n".join(text_components),
                files=files,
                embeds=legacy_embeds,
                components=legacy_reply_components
            )

    def sanitize_outbound(self, content: str) -> str:
        user_mentions = [item.split('>')[0] for item in content.split("<@")]
        channel_mentions = [item.split('>')[0] for item in content.split("<#")]
        emoji_mentions = [
                             item.split('>')[0].split(':')[1] for item in content.split("<:")
                         ] + [
                             item.split('>')[0].split(':')[1] for item in content.split("<a:")
                         ]

        for user_mention in user_mentions:
            # Check if this is a role mention
            if user_mention.startswith('&'):
                continue

            user = self.bot.get_user(int(user_mention))
            content.replace(f"<@{user_mention}>", f"@{user.global_name or user.name}")

        for channel_mention in channel_mentions:
            channel = self.bot.get_channel(int(channel_mention))
            content.replace(f"<#{channel_mention}>", f"#{channel.name}")

        for emoji_mention in emoji_mentions:
            emoji = self.bot.get_emoji(int(emoji_mention))
            content.replace(
                f"<a:{emoji.name}:{emoji_mention}>" if emoji.animated else f"<:{emoji.name}:{emoji_mention}>",
                f":{emoji.name}:"
            )

        return content

    def sanitize_inbound(self, content: str) -> str:
        """Nothing to sanitize"""
        return content

    # Beacon driver functions
    def get_user(self, user_id: str):
        user = self.bot.get_user(int(user_id))

        if not user:
            return None

        return self._to_beacon_user(user)

    async def fetch_user(self, user_id: str):
        user = await self.bot.fetch_user(int(user_id))

        return self._to_beacon_user(user)

    def _get_member(self, server: beacon_server.BeaconServer, member_id: str):
        discord_server = self.bot.get_guild(int(server.id))

        if not discord_server:
            return None

        member = discord_server.get_member(int(member_id))

        if not member:
            return None

        return self._to_beacon_member(member)

    def _get_channel(self, server: beacon_server.BeaconServer, channel_id: str):
        discord_server = self.bot.get_guild(int(server.id))

        if not discord_server:
            return None

        channel = discord_server.get_channel(int(channel_id))

        if not channel:
            return None

        return self._to_beacon_channel(channel)

    def get_server(self, server_id: str):
        server = self.bot.get_guild(int(server_id))

        if not server:
            return None

        return self._to_beacon_server(server)

    async def fetch_server(self, server_id: str):
        server = await self.bot.fetch_guild(int(server_id))

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
        webhook_obj: discord.Webhook | None = None
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
        discord_content: DiscordMessageContent = await self._to_discord_content(
            content, destination, use_components_v2=self._use_components_v2
        )

        # Convert bot user to BeaconUser
        self_user = self.get_user(str(self.bot.user.id))

        # Get target
        if webhook_id:
            target: discord.TextChannel | discord.abc.Messageable = webhook_obj.channel
        else:
            target: discord.TextChannel | discord.abc.Messageable = self.bot.get_channel(int(destination.id))

        # Convert channel to BeaconChannel
        channel: beacon_channel.BeaconChannel = self.get_channel(self.get_server(str(target.guild.id)), str(target.id))

        # Are we self-sending?
        if str(webhook_obj.channel_id) == content.original_channel_id and not self_send:
            # Return message object but don't send

            return beacon_message.BeaconMessage(
                message_id=content.original_id,
                platform=self.platform,
                author=send_as or self_user,
                server=self.get_server(str(target.guild.id)),
                channel=channel,
                content=discord_content.raw_content,
                attachments=len(discord_content.files),
                replies=[reply.get_message_for(channel) for reply in content.replies] if channel else [],
                webhook_id=webhook_id if webhook_obj else None
            )

        # Send the message!
        if webhook_id:
            if not target:
                return None

            message = await webhook_obj.send(
                content=discord_content.content,
                view=discord_content.components,
                embeds=discord_content.embeds,
                files=discord_content.files,
                username=custom_name,
                avatar_url=custom_avatar,
                wait=True
            )
        else:
            if not target:
                return None

            message = await target.send(
                content=discord_content.content,
                view=discord_content.components,
                embeds=discord_content.embeds,
                files=discord_content.files
            )

        return beacon_message.BeaconMessage(
            message_id=str(message.id),
            platform=self.platform,
            author=send_as or self_user,
            server=self.get_server(str(target.guild.id)),
            channel=channel,
            content=discord_content.raw_content,
            attachments=len(discord_content.files),
            replies=[reply.get_message_for(channel) for reply in content.replies] if channel else [],
            webhook_id=webhook_id if webhook_obj else None
        )

    async def _edit(self, message: beacon_message.BeaconMessage, content: beacon_message.BeaconMessageContent):
        channel = self.bot.get_channel(int(message.channel.id))
        message_obj = await channel.fetch_message(int(message.id))

        # Convert message content data
        discord_content: DiscordMessageContent = await self._to_discord_content(
            content, destination=message.channel, use_components_v2=self._use_components_v2
        )

        # Edit message
        await message_obj.edit(
            content=discord_content.content,
            view=discord_content.components,
            embeds=discord_content.embeds,
            files=discord_content.files
        )

    async def _delete(self, message: beacon_message.BeaconMessage):
        channel = self.bot.get_channel(int(message.channel.id))
        message_obj = await channel.fetch_message(int(message.id))

        # Delete message
        await message_obj.delete()
