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
import fluxer
from fluxer import cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.models import (space as beacon_space, driver as beacon_driver, server as beacon_server,
                                   channel as beacon_channel, webhook as beacon_webhook)

class BeaconFrontend(cog.Cog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(bot)

        # Get Beacon
        # noinspection PyUnresolvedReferences
        self._beacon: beacon.Beacon = self.bot.beacon

    @cog.Cog.command(name="new-space")
    async def new_space(self, ctx: fluxer.Message, name: str):
        if ctx.author.id != 1472271558005039139:
            return

        new_space: beacon_space.BeaconSpace = beacon_space.BeaconSpace(
            space_id=str(uuid.uuid4()),
            space_name=name
        )
        self._beacon.spaces.add_space(new_space)
        await ctx.send(f"space created!\n- id: `{new_space.id}`\n- name: {new_space.name}")

        loop = asyncio.get_event_loop()
        # noinspection PyTypeChecker
        await loop.run_in_executor(None, self._beacon.save_data)

    @cog.Cog.command(name="join-space")
    async def join_space(self, ctx: fluxer.Message, space_id: str):
        if ctx.author.id != 1472271558005039139:
            return

        space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)

        if not space:
            return await ctx.send("could not find space :c")

        fluxer_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("fluxer")

        # Get Beacon objects for server. channel and webhook
        server_obj: beacon_server.BeaconServer = fluxer_driver.get_server(str(ctx.guild_id))
        channel_obj: beacon_channel.BeaconChannel = fluxer_driver.get_channel(server_obj, str(ctx.channel_id))

        # Check if we're already in a space
        if self._beacon.spaces.get_space_for_channel(channel_obj):
            return await ctx.send("already in a space :/")

        webhook: fluxer.Webhook = await self.bot.create_webhook(
            name="Shinobu Bridge",
            channel_id=str(ctx.channel_id)
        )

        # Cache webhook
        fluxer_driver.webhooks.store_webhook(str(webhook.id), webhook)
        webhook_obj: beacon_webhook.BeaconWebhook = fluxer_driver.get_webhook(str(webhook.id))

        # Join space
        try:
            space.join(
                server=server_obj,
                channel=channel_obj,
                webhook=webhook_obj,
                force=True
            )
        except beacon_space.BeaconSpaceAlreadyJoined:
            return await ctx.send("already in space? :/")

        await ctx.send("space joined! :3")
        loop = asyncio.get_event_loop()
        # noinspection PyTypeChecker
        await loop.run_in_executor(None, self._beacon.save_data)

async def setup(bot):
    await bot.add_cog(BeaconFrontend(bot))
