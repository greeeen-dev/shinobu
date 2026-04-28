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
from functools import partial
from discord.ext import commands, bridge
from shinobu.runtime.models import shinobu_cog, ui_kit
from shinobu.beacon.protocol import beacon
from shinobu.beacon.models import (space as beacon_space, driver as beacon_driver, server as beacon_server,
                                   channel as beacon_channel, webhook as beacon_webhook)
from shinobu.runtime.models.ui_kit import ShinobuListEntry

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

    @bridge.bridge_group(name="bridge")
    async def bridge_universal(self, ctx):
        # Universal command group.
        pass

    @bridge_universal.command(name="new-space")
    @bridge.bridge_option("name", description="The name of the space.")
    @commands.is_owner() # Owner only for now for debugging purposes
    async def new_space(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext, *, name: str):
        """Creates a new Space."""

        new_space: beacon_space.BeaconSpace = beacon_space.BeaconSpace(
            space_id=str(uuid.uuid4()),
            space_name=name
        )
        self._beacon.spaces.add_space(new_space)
        await ctx.respond(f"space created!\n- id: `{new_space.id}`\n- name: {new_space.name}")
        await self.bot.loop.run_in_executor(None, self._beacon.save_data)

    @bridge_universal.command(name="delete-space")
    @bridge.bridge_option("space_id", description="The ID of the Space to delete.")
    @commands.is_owner()  # Owner only for now for debugging purposes
    async def delete_space(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext, space_id: str):
        """Deletes a Space."""

        try:
            self._beacon.spaces.delete_space(space_id)
        except KeyError:
            return await ctx.respond("could not find space :c")

        await ctx.respond(f"space deleted T.T")
        await self.bot.loop.run_in_executor(None, self._beacon.save_data)

    async def list_spaces_autocomplete(self, ctx: discord.AutocompleteContext) -> list[discord.OptionChoice]:
        priority_matches: list[str] = []
        matches: list[str] = []
        discord_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        for space in self._beacon.spaces.all_spaces:
            should_hide: bool = False
            if space.private:
                # Check if we have access to this space
                should_hide = not space.has_access(
                    discord_driver.get_server(str(ctx.interaction.guild.id))
                ) if ctx.interaction.guild else True

            if should_hide:
                continue

            if space.name.lower().startswith(ctx.value.lower()):
                priority_matches.append(f"{space.name} ({space.id})")
            elif ctx.value.lower() in space.name.lower():
                matches.append(f"{space.name} ({space.id})")
            elif ctx.value.lower() == space.id:
                priority_matches.insert(0, f"{space.name} ({space.id})")
            elif len(ctx.value) == 0:
                matches.append(f"{space.name} ({space.id})")

        all_matches: list[str] = priority_matches + matches

        return [
            discord.OptionChoice(name=all_matches[i]) for i in range(len(all_matches) if len(all_matches) <= 25 else 25)
        ]

    @bridge_universal.command(name="spaces")
    @bridge.bridge_option("query", description="The search query. Leave empty to list all Spaces.",
                          autocomplete=partial(list_spaces_autocomplete))
    async def list_spaces(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext, query: str | None = None):
        """Shows all available Spaces."""

        # Get driver
        discord_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        # Create new list UI
        list_ui: ui_kit.ShinobuListDiscordView = ui_kit.ShinobuListDiscordView(
            ":house: available spaces",
            "This is a list of all Spaces your server can access.",
            self.bot.colors.shinobu,
            allow_hidden=ctx.user.id == self.bot.owner_id
        )

        # Add spaces
        for space in self._beacon.spaces.all_spaces:
            should_hide: bool = False
            if space.private:
                # Check if we have access to this space
                should_hide = not space.has_access(discord_driver.get_server(str(ctx.guild.id))) if ctx.guild else True

            entry: ShinobuListEntry = ShinobuListEntry(
                entry_id=space.id,
                name=space.name,
                emoji=space.emoji,
                hidden=should_hide
            )
            entry.add_field(
                name="Space ID",
                value=f"`{space.id}`"
            )

            list_ui.add_entry(entry)

        # Run loop
        await list_ui.run(self.bot, ctx, query=query)

    @bridge_universal.command(name="join-space")
    @bridge.bridge_option("space_id", description="The ID or invite of the Space to join.")
    @commands.is_owner()
    async def join_space(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext, space_id: str):
        """Joins a Space."""

        space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)

        if not space:
            return await ctx.respond("could not find space :c")

        discord_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        # Get Beacon objects for server, channel and webhook
        server_obj: beacon_server.BeaconServer = discord_driver.get_server(str(ctx.guild.id))
        channel_obj: beacon_channel.BeaconChannel = discord_driver.get_channel(server_obj, str(ctx.channel.id))

        # Check if we're already in a space
        if self._beacon.spaces.get_space_for_channel(channel_obj):
            return await ctx.respond("already in a space :/")

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
            return await ctx.respond("already in space? :/")

        await ctx.respond("space joined! :3")
        await self.bot.loop.run_in_executor(None, self._beacon.save_data)

    @bridge_universal.command(name="leave-space")
    @bridge.bridge_option("space_id", description="The ID of the Space to leave.")
    @commands.is_owner()
    async def leave_space(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext, space_id: str):
        """Leaves a Space."""

        # noinspection DuplicatedCode
        space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)

        if not space:
            return await ctx.respond("could not find space :c")

        discord_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")

        # Get Beacon server obect
        server_obj: beacon_server.BeaconServer = discord_driver.get_server(str(ctx.guild.id))

        # Get space membership
        membership: beacon_space.BeaconSpaceMember | None = space.get_member(server_obj)
        if not membership:
            return await ctx.respond("you are not a member of this space :/")

        # Get webhook
        webhook: discord.Webhook | None = None

        # noinspection PyBroadException
        try:
            await discord_driver.getch_webhook(membership.webhook_id)
        except:
            pass
        else:
            webhook = discord_driver.webhooks.get_webhook(membership.webhook_id)

        # Leave space
        try:
            space.leave(membership)
        except beacon_space.BeaconSpaceNotJoined:
            # This should not raise, but let's handle it anyway
            return await ctx.respond("you are not a member of this space :/")

        await ctx.respond("space left :<")
        await self.bot.loop.run_in_executor(None, self._beacon.save_data)

        # Delete webhook
        if webhook:
            await webhook.delete()

def get_cog_type():
    return BeaconFrontend

def setup(bot):
    bot.add_cog(BeaconFrontend(bot))
