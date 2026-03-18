import asyncio
import aiohttp
import fluxer
from datetime import datetime
from fluxer import cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.models import (message as beacon_message, content as beacon_content, file as beacon_file,
                                   driver as beacon_driver, server as beacon_server, channel as beacon_channel,
                                   member as beacon_member, space as beacon_space)

class FluxerEvents(cog.Cog):
    def __init__(self, bot):
        super().__init__(bot)

    async def _to_beacon_content(self, message: fluxer.Message) -> beacon_message.BeaconMessageContent:
        # noinspection PyUnresolvedReferences
        origin_driver: beacon_driver.BeaconDriver = self.bot.beacon.drivers.get_driver("fluxer")

        # Create text content block
        text_content: beacon_content.BeaconContentText = beacon_content.BeaconContentText(
            content=origin_driver.sanitize_outbound(message.content)
        )

        # Create embed blocks
        embed_blocks: list[beacon_content.BeaconContentEmbed] = []
        for embed_dict in message.embeds:
            # Only handle rich embeds
            if embed_dict["type"] != "rich":
                continue

            embed: fluxer.Embed = fluxer.Embed.from_data(embed_dict)
            embed_block: beacon_content.BeaconContentEmbed = beacon_content.BeaconContentEmbed(
                title=embed.title,
                description=embed.description,
                url=embed.url,
                color=embed.color
            )

            if embed.author:
                embed_block.set_author(
                    text=embed.author.get("name"),
                    url=embed.author.get("url"),
                    icon_url=embed.author.get("icon_url")
                )

            if embed.footer:
                embed_block.set_footer(
                    text=embed.footer.get("text"),
                    icon_url=embed.footer.get("icon_url")
                )

            if embed.timestamp:
                embed_block.timestamp = int(datetime.fromisoformat(embed.timestamp).timestamp())

            if embed.fields:
                for field in embed.fields:
                    embed_block.add_field(
                        name=field["name"],
                        value=field["value"],
                        inline=field["inline"]
                    )

            # Add to embed blocks
            embed_blocks.append(embed_block)

        # Add reply if it exists
        replies: list[beacon_message.BeaconMessageGroup] = []
        reply_content: str | None = None
        reply_attachments: int = 0

        if message.referenced_message:
            # noinspection PyUnresolvedReferences
            reply_group: beacon_message.BeaconMessageGroup | None = self.bot.beacon.messages.get_group_from_message(
                str(message.referenced_message.id)
            )
            if reply_group:
                replies.append(reply_group)

        if message.referenced_message and len(replies) > 0:
            reply_message: fluxer.Message = message.referenced_message
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
            original_platform="fluxer",
            blocks=blocks,
            files=files,
            replies=replies,
            reply_content=origin_driver.sanitize_outbound(reply_content) if reply_content else None,
            reply_attachments=reply_attachments
        )

        return content

    @staticmethod
    async def _get_attachment_data(attachment: fluxer.models.Attachment) -> beacon_file.BeaconFile:
        url: str = attachment.url
        proxy_url: str | None = attachment.proxy_url
        filename: str = attachment.filename
        media: bool = 'image/' in attachment.content_type or 'video/' in attachment.content_type
        data: bytes | None = None

        session = aiohttp.ClientSession()
        async with session.get(proxy_url or url) as response:
            if response.status == 200:
                data = await response.read()
            else:
                raise RuntimeError(f"Failed to fetch data: {response.status}")
        await session.close()

        return beacon_file.BeaconFile(
            data=data,
            url=url,
            media=media,
            filename=filename,
        )

    async def handle_edit(self, message: fluxer.Message):
        # noinspection PyUnresolvedReferences
        beacon_obj: beacon.Beacon = self.bot.beacon

        origin_driver: beacon_driver.BeaconDriver = beacon_obj.drivers.get_driver("fluxer")

        # Get the BeaconMessage object for the message
        message_obj: beacon_message.BeaconMessage = beacon_obj.messages.get_message(str(message.id))

        # Did we bridge this message?
        if message.webhook_id:
            if message_obj.author.id != str(message.webhook_id):
                # We probably did
                return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.guild_id))

        # Convert author data to member.BeaconMember
        author: beacon_member.BeaconMember = origin_driver.get_member(server, str(message.author.id))

        # Convert channel data to channel.BeaconChannel
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(message.channel.id))

        # Get Space
        space: beacon_space.BeaconSpace = beacon_obj.spaces.get_space_for_channel(channel)

        # Get the ID of the webhook to use
        membership: beacon_space.BeaconSpaceMember = space.get_member(server)
        webhook_id = membership.webhook_id

        if not space:
            # We can't bridge
            return

        # Convert message data to message.BeaconMessageContent
        content: beacon_message.BeaconMessageContent = await self._to_beacon_content(message)

        # Run preliminary checks
        preliminary_block: beacon.BeaconMessageBlockedReason | None = await beacon_obj.can_send(
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
            await beacon_obj.edit(
                message=message_obj,
                content=content
            )
        except beacon.BeaconPlatformDisabled:
            pass

    async def handle_delete(self, message: dict):
        # noinspection PyUnresolvedReferences
        beacon_obj: beacon.Beacon = self.bot.beacon

        origin_driver: beacon_driver.BeaconDriver = beacon_obj.drivers.get_driver("discord")

        # Get the BeaconMessage object for the message
        message_obj: beacon_message.BeaconMessage = beacon_obj.messages.get_message(str(message["id"]))
        if not message_obj:
            # We can't remove messages that aren't cached
            return

        # Check if author ID exists
        # This may not be in the data for webhook messages for some reason :/
        if not message.get("author_id"):
            return

        # Did we bridge this message?
        if message.get("webhook_id"):
            if message_obj.author.id != str(message["webhook_id"]):
                # We probably did
                return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message["guild_id"]))

        # Convert channel data to channel.BeaconChannel
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(message["channel_id"]))

        # Get Space
        space: beacon_space.BeaconSpace = beacon_obj.spaces.get_space_for_channel(channel)

        if not space:
            # We can't bridge deletes, even if it was sent in the Space by the server
            return

        # Delete the message!
        try:
            await beacon_obj.delete(message=message_obj)
        except beacon.BeaconPlatformDisabled:
            pass

    @cog.Cog.listener()
    async def on_ready(self):
        print(f"Logged in to Fluxer as {self.bot.user.username}#{self.bot.user.discriminator} ({self.bot.user.id})")

        # We'll wait 0.5s before registering driver so GUILD_CREATE events have time to be received and handled
        await asyncio.sleep(0.5)

        # noinspection PyUnresolvedReferences
        self.bot.register_driver()

    @cog.Cog.listener()
    async def on_message(self, message):
        # noinspection PyUnresolvedReferences
        origin_driver: beacon_driver.BeaconDriver = self.bot.beacon.drivers.get_driver("fluxer")

        # noinspection DuplicatedCode
        if message.content.startswith(self.bot.command_prefix):
            # Assume this is a text command
            return

        if message.author.id == self.bot.user.id:
            # Do not self-bridge
            return

        if message.webhook_id:
            # Check if the webhook was ours (to prevent a self-bridge)
            webhook: fluxer.Webhook | None = origin_driver.webhooks.get_webhook(str(message.webhook_id))

            if not webhook:
                try:
                    webhook = await self.bot.fetch_webhook(message.webhook_id)
                    origin_driver.webhooks.store_webhook(str(webhook.id), webhook)
                except fluxer.HTTPException:
                    pass

            if webhook:
                # Does the bot own the webhook?
                if webhook.user.id == self.bot.user.id:
                    # Do not self-bridge
                    return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(str(message.guild_id))

        # Convert channel data to channel.BeaconChannel
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, str(message.channel_id))

        # Get Space
        # noinspection PyUnresolvedReferences
        space: beacon_space.BeaconSpace = self.bot.beacon.spaces.get_space_for_channel(channel)
        if not space:
            # We can't bridge
            return

        # Convert author data to member.BeaconMember
        author: beacon_member.BeaconMember | None = origin_driver.get_member(server, str(message.author.id))

        if not author:
            # Fetch then retry
            fluxer_guild = self.bot.get_guild(message.guild_id)
            await fluxer_guild.fetch_member(str(message.author.id))
            author = origin_driver.get_member(server, str(message.author.id))

        # Get the ID of the webhook to use
        membership: beacon_space.BeaconSpaceMember = space.get_member(server)
        webhook_id = membership.webhook_id

        # Convert message data to message.BeaconMessageContent
        content: beacon_message.BeaconMessageContent = await self._to_beacon_content(message)

        # Run preliminary checks
        # noinspection PyUnresolvedReferences
        preliminary_block: beacon.BeaconMessageBlockedReason | None = await self.bot.beacon.can_send(
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
        try:
            # noinspection PyUnresolvedReferences
            await self.bot.beacon.send(
                author=author,
                space=space,
                content=content,
                webhook_id=webhook_id
            )
        except beacon.BeaconPlatformDisabled:
            pass

    @cog.Cog.listener()
    async def on_message_edit(self, message: fluxer.Message):
        # noinspection PyUnresolvedReferences
        beacon_obj: beacon.Beacon = self.bot.beacon

        # Check if message is pending
        if beacon_obj.is_pending(str(message.id)):
            # Add callback
            beacon_obj.add_callback(str(message.id), self.handle_edit, [message])
        else:
            # Run directly
            await self.handle_edit(message)

    @cog.Cog.listener()
    async def on_message_delete(self, message: dict):
        # noinspection PyUnresolvedReferences
        beacon_obj: beacon.Beacon = self.bot.beacon

        # Check if message is pending
        if beacon_obj.is_pending(str(message["id"])):
            # Add callback
            beacon_obj.add_callback(str(message["id"]), self.handle_delete, [message])
        else:
            # Run directly
            await self.handle_delete(message)

    @cog.Cog.listener()
    async def on_message_delete_bulk(self, data: dict):
        server_id: str = data["guild_id"]
        channel_id: str = data["channel_id"]
        message_ids: list[int] = [int(message_id) for message_id in data.get("ids", [])]

        # noinspection PyUnresolvedReferences
        beacon_obj: beacon.Beacon = self.bot.beacon

        # noinspection DuplicatedCode
        origin_driver: beacon_driver.BeaconDriver = beacon_obj.drivers.get_driver("fluxer")

        to_delete: list[beacon_message.BeaconMessage] = []

        # Get messages
        for message_id in message_ids:
            # Get the BeaconMessage object for the message
            message_obj: beacon_message.BeaconMessage = beacon_obj.messages.get_message(str(message_id))
            if not message_obj:
                # We can't remove messages that aren't cached
                continue

            # Did we bridge this message?
            # Usually we'd use the native message object as our source-of-truth, but that isn't
            # possible here, so we'll have to resort to this
            if message_obj.webhook_id:
                # Get webhook
                await origin_driver.getch_webhook(message_obj.webhook_id)
                webhook: fluxer.Webhook = origin_driver.webhooks.get_webhook(message_obj.webhook_id)

                if webhook.user.id == self.bot.user.id:
                    # We probably did
                    continue

            to_delete.append(message_obj)

        if len(to_delete) == 0:
            # We have nothing to delete
            return

        # Convert guild data to server.BeaconServer
        server: beacon_server.BeaconServer = origin_driver.get_server(server_id)

        # Convert channel data to channel.BeaconChannel
        # noinspection DuplicatedCode
        channel: beacon_channel.BeaconChannel = origin_driver.get_channel(server, channel_id)
        if not channel:
            # We can't bridge
            return

        # Get Space
        space: beacon_space.BeaconSpace = beacon_obj.spaces.get_space_for_channel(channel)

        if not space:
            # We can't bridge deletes, even if it was sent in the Space by the server
            return

        # Delete the messages!
        try:
            await beacon_obj.purge(messages=to_delete)
        except beacon.BeaconPlatformDisabled:
            pass

async def setup(bot):
    await bot.add_cog(FluxerEvents(bot))