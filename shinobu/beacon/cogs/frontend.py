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

import uuid
import discord
from discord.ext import commands
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.models import (space as beacon_space, driver as beacon_driver, server as beacon_server,
                                   channel as beacon_channel, webhook as beacon_webhook)

class BeaconFrontend(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Bridge",
                description="A module containing commands for bridge setup.",
                emoji="\U0001F4E1",
                visible_in_help=True
            )
        )

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")

    @commands.group(name='bridge')
    async def bridge_text(self, ctx):
        pass

    @bridge_text.command(name="new-space")
    @commands.is_owner() # Owner only for now for debugging purposes
    async def new_space(self, ctx: commands.Context, name: str):
        new_space: beacon_space.BeaconSpace = beacon_space.BeaconSpace(
            space_id=str(uuid.uuid4()),
            space_name=name
        )
        self._beacon.spaces.add_space(new_space)
        await ctx.send(f"space created!\n- id: `{new_space.id}`\n- name: {new_space.name}")
        await self.bot.loop.run_in_executor(None, self._beacon.save_data)

    @bridge_text.command(name="join-space")
    @commands.is_owner()
    async def join_space(self, ctx: commands.Context, space_id: str):
        space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)

        if not space:
            return await ctx.send("could not find space :c")

        discord_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        # Get Beacon objects for server. channel and webhook
        server_obj: beacon_server.BeaconServer = discord_driver.get_server(str(ctx.guild.id))
        channel_obj: beacon_channel.BeaconChannel = discord_driver.get_channel(server_obj, str(ctx.channel.id))

        # Check if we're already in a space
        if self._beacon.spaces.get_space_for_channel(channel_obj):
            return await ctx.send("already in a space :/")

        webhook: discord.Webhook = await ctx.channel.create_webhook(
            name="Shinobu Bridge"
        )

        # Cache webhook
        discord_driver.webhooks.store_webhook(str(webhook.id), webhook)
        webhook_obj: beacon_webhook.BeaconWebhook = discord_driver.get_webhook(str(webhook.id))

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
        await self.bot.loop.run_in_executor(None, self._beacon.save_data)

def get_cog_type():
    return BeaconFrontend

def setup(bot):
    bot.add_cog(BeaconFrontend(bot))
