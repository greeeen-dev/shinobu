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
from shinobu.beacon.models import (space as beacon_space, driver as beacon_driver, server as beacon_server,
                                   channel as beacon_channel, webhook as beacon_webhook, beacon_cog)
from shinobu.beacon.utils.checks import CommandChecks

class BeaconFrontend(beacon_cog.BeaconCog):
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

    @bridge.bridge_group(name="bridge")
    async def bridge_universal(self, ctx):
        # Universal command group.
        pass

    @bridge_universal.command(name="new-space")
    @bridge.bridge_option("name", description="The name of the space.")
    @commands.guild_only()
    @CommandChecks.can_manage()
    async def new_space(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext, *, name: str,
                        public: bool | None = None):
        """Creates a new Space."""

        private_available: bool = (
            self._beacon.can_create_private_space or
            self.bot.owner_id == ctx.author.id or
            ctx.author.id in self.bot.owner_ids
        )
        public_available: bool = (
            self._beacon.can_create_public_space or
            self.bot.owner_id == ctx.author.id or
            ctx.author.id in self.bot.owner_ids
        )

        # Check if room creation is possible
        if not public_available and not private_available:
            return await ctx.respond("space creations are disabled :c", ephemeral=True)

        if public is None:
            # We'll go with whatever is available
            if private_available:
                public = False
            elif public_available:
                public = True

        if public and not public_available:
            return await ctx.respond("public space creations are disabled :c", ephemeral=True)
        elif not public and not private_available:
            return await ctx.respond("public space creations are disabled :c", ephemeral=True)

        new_space: beacon_space.BeaconSpace = beacon_space.BeaconSpace(
            space_id=str(uuid.uuid4()),
            space_name=name,
            private=not public,
            owner_id=str(ctx.guild.id),
            owner_platform="discord"
        )
        self._beacon.spaces.add_space(new_space)
        await ctx.respond(f"space created!\n- id: `{new_space.id}`\n- name: {new_space.name}")
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

        if len(ctx.value) > 0:
            matches.append(ctx.value)

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

            entry: ui_kit.ShinobuListEntry = ui_kit.ShinobuListEntry(
                entry_id=space.id,
                name=space.name,
                description=space.description,
                emoji=space.emoji,
                hidden=should_hide
            )
            entry.add_field(
                name="Space ID",
                value=f"`{space.id}`"
            )

            if space.private:
                entry.add_field(
                    name=":lock: Private Space",
                    value="This Space is private. Servers will need a valid invite to join this Space."
                )
            else:
                entry.add_field(
                    name=":globe_with_meridians: Public Space",
                    value="This Space is public. Servers can join this Space without an invite."
                )

            if space.nsfw:
                entry.add_field(
                    name=":underage: Age-gated space",
                    value="This Space is marked as age-gated. Only age-gated channels may join and talk in this Space."
                )

            list_ui.add_entry(entry)

        # Run loop
        await list_ui.run(self.bot, ctx, query=query)

    @bridge_universal.command(name="join-space")
    @bridge.bridge_option("space_id", description="The ID or invite of the Space to join. An invite is required for private Spaces.")
    @commands.guild_only()
    @CommandChecks.can_manage()
    async def join_space(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext, space_id: str):
        """Joins a Space."""

        space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)
        can_override: bool = False
        invite: beacon_space.BeaconSpaceInvite | None = None

        if space.private:
            # Check if we can override this
            can_override = self.can_force_join(ctx.user.id)

        if not space:
            # Check if this is an invite
            invite = self._beacon.spaces.get_invite(space_id)

            if invite:
                space = self._beacon.spaces.get_space_for_invite(invite)

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
                invite=invite,
                force=can_override
            )
        except beacon_space.BeaconSpaceAlreadyJoined:
            return await ctx.respond("already in space? :/")

        await ctx.respond("space joined! :3")
        await self.bot.loop.run_in_executor(None, self._beacon.save_data)

    @bridge_universal.command(name="leave-space")
    @bridge.bridge_option("space_id", description="The ID of the Space to leave.")
    @commands.guild_only()
    @CommandChecks.can_manage()
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

    @bridge_universal.command(name="delete-space")
    @bridge.bridge_option("space_id", description="The ID of the Space to delete.")
    @CommandChecks.can_manage()
    async def delete_space(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext,
                           space_id: str):
        """Shows options for a Space."""

        # Get space
        space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)

        if not self.can_manage(space, ctx.guild.id, user_id=ctx.author.id):
            raise commands.CheckFailure()

        embed: discord.Embed = discord.Embed(
            title=":warning: ARE YOU SURE?",
            description=f"This will delete {space.decorated_name} (`{space.id}`). Once it's gone, it's gone forever!",
            color=self.bot.colors.warning
        )
        embed.set_footer(
            text=f"If you need to edit the Space, use /config space-options space_id:{space.id} instead!"
        )

        view: discord.ui.View = discord.ui.View()
        view.add_item(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="I'm sure!",
                    style=discord.ButtonStyle.red,
                    custom_id="danger_confirm"
                ),
                discord.ui.Button(
                    label="No thanks",
                    style=discord.ButtonStyle.gray,
                    custom_id="danger_backout"
                )
            )
        )

        result: discord.Message | discord.Interaction = await ctx.respond(embed=embed, view=view)

        if isinstance(result, discord.Interaction):
            message: discord.InteractionMessage = await result.original_response()
        else:
            message: discord.Message = result

        confirmed, interaction = await self.confirm_danger(ctx, message)

        if confirmed:
            # Delete space
            self._beacon.spaces.delete_space(space.id)

            embed.title = ":wastebasket: Gone, reduced to atoms."
            embed.description = f"{space.decorated_name} was deleted and is no more. It will be missed."
            embed.colour = self.bot.colors.success
            embed.set_footer(text=None)
            await interaction.response.edit_message(embed=embed, view=None)
            await self.bot.loop.run_in_executor(None, self._beacon.save_data)
        else:
            if interaction:
                await interaction.response.edit_message(view=None)
            else:
                return await message.edit(view=None)

def get_cog_type():
    return BeaconFrontend

def setup(bot):
    bot.add_cog(BeaconFrontend(bot))
