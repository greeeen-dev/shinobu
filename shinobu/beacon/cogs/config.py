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
from discord.ext import bridge, commands
from shinobu.runtime.models import shinobu_cog, errors
from shinobu.beacon.protocol import beacon
from shinobu.beacon.models import space as beacon_space, driver as beacon_driver, user as beacon_user
from shinobu.beacon.utils.checks import CommandChecks

class BeaconConfig(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Config",
                description="A module containing configuration commands.",
                emoji="\U0001F4E1",
                visible_in_help=True
            )
        )

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")

    def can_manage(self, space: beacon_space.BeaconSpace, guild_id: int, user_id: int | None = None):
        is_admin: bool = False
        if user_id:
            platform_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")
            user_obj: beacon_user.BeaconUser | None = platform_driver.get_user(str(user_id))

            if user_obj:
                is_admin = self._beacon.moderators.is_admin(user_obj)

        return (
            space.owner_id == str(guild_id) and space.owner_platform == "discord" or
            is_admin or
            user_id == self.bot.owner_id or
            user_id in self.bot.owner_ids
        )

    @staticmethod
    def create_button(custom_id: str | None = None, state: bool = False, disabled: bool = False):
        return discord.ui.Button(
            style=discord.ButtonStyle.green if state else discord.ButtonStyle.gray,
            label="On" if state else "Off",
            emoji="\U00002705" if state else "\U0000274C",
            custom_id=custom_id,
            disabled=disabled
        )

    def autodetect(self, channel: discord.TextChannel) -> beacon_space.BeaconSpace | None:
        for space in self._beacon.spaces.all_spaces:
            memberships: list[beacon_space.BeaconSpaceMember] = [
                member for member in space.members
                if member.channel_id == str(channel.id) and member.platform == "discord"
            ]
            if len(memberships) > 0:
                return space

        return None

    @bridge.bridge_group(name="config")
    async def config_universal(self, ctx):
        # Universal command group.
        pass

    @config_universal.command(name="relay-options")
    @bridge.bridge_option("space_id", description="The Space ID. Leave empty to use the Space linked to this channel.")
    @CommandChecks.can_manage()
    async def relay_options(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext,
                            space_id: str | None = None):
        if not space_id:
            # Try to autodetect space
            space: beacon_space.BeaconSpace | None = self.autodetect(ctx.channel)
        else:
            space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)

        if not space:
            raise errors.ShinobuNotFound("space_id")

        if not self.can_manage(space, ctx.guild.id, user_id=ctx.author.id):
            raise commands.CheckFailure()

        interaction: discord.Interaction | None = None
        message: discord.Message | None = None
        is_done: bool = False

        while True:
            # Render view
            view: discord.ui.DesignerView = discord.ui.DesignerView(store=False)
            container: discord.ui.Container = discord.ui.Container(color=self.bot.colors.shinobu)

            # Add text
            container.add_text(f"### :gear: relay options for {space.decorated_name}")
            container.add_text("Manage your Space's relay options here.")

            # Add options
            container.add_section(
                discord.ui.TextDisplay(
                    "**:pencil: Relay edits**\n"+
                    "When enabled, message edits will be relayed to connected servers."
                ),
                accessory=self.create_button("toggle_edits", space.relay_edits, disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:wastebasket: Relay deletes**\n" +
                    "When enabled, message deletes (including purges) will be relayed to connected servers."
                ),
                accessory=self.create_button("toggle_deletes", space.relay_deletes, disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:pushpin: Relay pins**\n" +
                    "When enabled, message pins will be relayed to connected servers."
                ),
                accessory=self.create_button("toggle_pins", space.relay_pins, disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:truck: Relay large files**\n" +
                    "When enabled, large files too big to bridge may be bridged as links."
                ),
                accessory=self.create_button("toggle_large_attachment", space.convert_large_files, disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:clock3: Compatibility mode**\n" +
                    "Changes bridge behavior to stay friendly with legacy clients."
                ),
                accessory=self.create_button("toggle_compatibility", space.compatibility, disabled=is_done)
            )

            view.add_item(container)

            if not interaction:
                if is_done:
                    await message.edit(view=view)
                else:
                    result: discord.Message | discord.Interaction = await ctx.respond(view=view)

                    if isinstance(result, discord.Interaction):
                        message = await result.original_response()
                    else:
                        message = result
            else:
                if interaction.response.is_done():
                    await message.edit(view=view)
                else:
                    await interaction.response.edit_message(view=view)

            if is_done:
                await self.bot.loop.run_in_executor(None, lambda: self._beacon.save_data())
                break

            def check(incoming: discord.Interaction):
                if not incoming.message:
                    return False

                return incoming.user.id == ctx.author.id and incoming.message.id == message.id

            try:
                interaction = await self.bot.wait_for("interaction", check=check, timeout=60)
            except asyncio.TimeoutError:
                is_done = True
                continue

            if interaction.custom_id == "toggle_edits":
                space.relay_edits = not space.relay_edits
            elif interaction.custom_id == "toggle_deletes":
                space.relay_deletes = not space.relay_deletes
            elif interaction.custom_id == "toggle_pins":
                space.relay_pins = not space.relay_pins
            elif interaction.custom_id == "toggle_large_attachment":
                space.convert_large_files = not space.convert_large_files
            elif interaction.custom_id == "toggle_compatibility":
                space.compatibility = not space.compatibility

def get_cog_type():
    return BeaconConfig

def setup(bot):
    bot.add_cog(BeaconConfig(bot))
