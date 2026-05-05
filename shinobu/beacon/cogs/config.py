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
import emoji
from discord.ext import bridge, commands
from shinobu.runtime.models import shinobu_cog, errors
from shinobu.beacon.models import space as beacon_space, beacon_cog
from shinobu.beacon.utils.checks import CommandChecks

class BeaconConfig(beacon_cog.BeaconCog):
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

    @staticmethod
    def create_edit_button(custom_id: str | None = None, disabled: bool = False):
        return discord.ui.Button(
            style=discord.ButtonStyle.blurple,
            label="Edit",
            emoji="\U0000270F\U0000FE0F",
            custom_id=custom_id,
            disabled=disabled
        )

    @staticmethod
    def create_toggle_button(custom_id: str | None = None, state: bool = False, disabled: bool = False):
        return discord.ui.Button(
            style=discord.ButtonStyle.green if state else discord.ButtonStyle.gray,
            label="On" if state else "Off",
            emoji="\U00002705" if state else "\U0000274C",
            custom_id=custom_id,
            disabled=disabled
        )

    @staticmethod
    def create_modal(title: str | None = None, custom_id: str | None = None, label: str | None = None,
                     placeholder: str | None = None, default: str | None = None, input_custom_id: str | None = None,
                     long: bool = False, minimum: int | None = None, maximum: int | None = None, required: bool = True):
        modal: discord.ui.Modal = discord.ui.Modal(
            title=title,
            custom_id=custom_id,
            store=False
        )
        input_text = discord.ui.InputText(
            label=label,
            placeholder=placeholder,
            value=default,
            style=discord.InputTextStyle.long if long else discord.InputTextStyle.short,
            custom_id=input_custom_id,
            min_length=minimum,
            max_length=maximum,
        )
        input_text.required = required
        modal.add_item(input_text)

        return modal

    def autodetect(self, channel: discord.TextChannel, space_id: str | None) -> beacon_space.BeaconSpace | None:
        if space_id:
            space: beacon_space.BeaconSpace | None = self._beacon.spaces.get_space(space_id)
            if not space:
                raise errors.ShinobuNotFound("space_id")

            return space

        for space in self._beacon.spaces.all_spaces:
            memberships: list[beacon_space.BeaconSpaceMember] = [
                member for member in space.members
                if member.channel_id == str(channel.id) and member.platform == "discord"
            ]
            if len(memberships) > 0:
                return space

        raise errors.ShinobuNotFound("space_id")

    @bridge.bridge_group(name="config")
    async def config_universal(self, ctx):
        # Universal command group.
        pass

    @config_universal.command(name="space-options")
    @bridge.bridge_option("space_id", description="The Space ID. Leave empty to use the Space linked to this channel.")
    @CommandChecks.can_manage()
    async def space_options(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext,
                            space_id: str | None = None):
        """Shows options for a Space."""

        # Get space
        space: beacon_space.BeaconSpace = self.autodetect(ctx.channel, space_id)

        if not self.can_manage(space, ctx.guild.id, user_id=ctx.author.id):
            raise commands.CheckFailure()

        interaction: discord.Interaction | None = None
        message: discord.Message | None = None
        is_done: bool = False
        skip_edit: bool = False
        skip_response: bool = False

        while True:
            # Render view
            view: discord.ui.DesignerView = discord.ui.DesignerView(store=False)
            container: discord.ui.Container = discord.ui.Container(color=self.bot.colors.shinobu)

            # Add text
            container.add_text(f"### :gear: space options for {space.decorated_name}")
            container.add_text("Manage your Space here.")

            # Add general options
            container.add_text("### Space settings")
            container.add_section(
                discord.ui.TextDisplay(
                    "**:heart: Space name**\n" +
                    f"Current name: **{space.name}**"
                ),
                accessory=self.create_edit_button("edit_name", disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:scroll: Space description**\n" +
                    "Current description:" + (
                        f"\n{space.quoted_description}" if space.description else " *No description provided*"
                    )
                ),
                accessory=self.create_edit_button("edit_description", disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    f"**{space.emoji or ':thinking:'} Space emoji**\n" +
                    "Current emoji: " + (
                        f"`{space.emoji}`" if space.emoji else "*No emoji provided*"
                    )
                ),
                accessory=self.create_edit_button("edit_emoji", disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:underage: Age-gated space**\n" +
                    "Allow only age-gated channels to connect to this Space."
                ),
                accessory=self.create_toggle_button(
                    "toggle_nsfw",
                    space.nsfw,
                    disabled=is_done or (not self._beacon.allow_agegated_spaces and not space.nsfw)
                )
            )

            # Add relay options
            container.add_text("### Relay options")
            container.add_section(
                discord.ui.TextDisplay(
                    "**:pencil: Relay edits**\n"+
                    "When enabled, message edits will be relayed to connected servers."
                ),
                accessory=self.create_toggle_button("toggle_edits", space.relay_edits, disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:wastebasket: Relay deletes**\n" +
                    "When enabled, message deletes (including purges) will be relayed to connected servers."
                ),
                accessory=self.create_toggle_button("toggle_deletes", space.relay_deletes, disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:pushpin: Relay pins**\n" +
                    "When enabled, message pins will be relayed to connected servers."
                ),
                accessory=self.create_toggle_button("toggle_pins", space.relay_pins, disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:truck: Relay large files**\n" +
                    "When enabled, large files too big to bridge may be bridged as links."
                ),
                accessory=self.create_toggle_button("toggle_large_attachment", space.convert_large_files, disabled=is_done)
            )
            container.add_section(
                discord.ui.TextDisplay(
                    "**:clock3: Compatibility mode**\n" +
                    "Changes bridge behavior to stay friendly with legacy clients."
                ),
                accessory=self.create_toggle_button("toggle_compatibility", space.compatibility, disabled=is_done)
            )

            view.add_item(container)

            if not interaction:
                if is_done and not skip_edit:
                    await message.edit(view=view)
                else:
                    result: discord.Message | discord.Interaction = await ctx.respond(view=view)

                    if isinstance(result, discord.Interaction):
                        message = await result.original_response()
                    else:
                        message = result
            elif not skip_edit and not skip_response:
                if interaction.response.is_done():
                    await message.edit(view=view)
                else:
                    await interaction.response.edit_message(view=view)

            skip_edit = False
            skip_response = False

            if is_done:
                await self.bot.loop.run_in_executor(None, lambda: self._beacon.save_data())
                break

            def check(incoming: discord.Interaction):
                if not incoming.message:
                    return False

                return incoming.user.id == ctx.author.id and incoming.message.id == message.id

            try:
                interaction = await self.bot.wait_for("interaction", check=check, timeout=120)
            except asyncio.TimeoutError:
                is_done = True
                continue

            if space.deleted:
                await interaction.response.send_message(
                    "this space was deleted while you were editing it :c", ephemeral=True
                )
                is_done = True
                continue

            # Toggle buttons
            match interaction.custom_id:
                case "toggle_nsfw":
                    space.nsfw = not space.nsfw
                case "toggle_edits":
                    space.relay_edits = not space.relay_edits
                case "toggle_deletes":
                    space.relay_deletes = not space.relay_deletes
                case "toggle_pins":
                    space.relay_pins = not space.relay_pins
                case "toggle_large_attachment":
                    space.convert_large_files = not space.convert_large_files
                case "toggle_compatibility":
                    space.compatibility = not space.compatibility

            # Edit buttons
            if interaction.custom_id.startswith("edit_"):
                skip_edit = True
                modal: discord.ui.Modal | None = None

                match interaction.custom_id:
                    case "edit_name":
                        modal = self.create_modal(
                            title=f"Edit name for {space.decorated_name}",
                            custom_id="modal_name",
                            label="Space name",
                            placeholder="Enter a name...",
                            default=space.name,
                            input_custom_id="input"
                        )
                    case "edit_description":
                        modal = self.create_modal(
                            title=f"Edit description for {space.decorated_name}",
                            custom_id="modal_description",
                            label="Space description",
                            placeholder="Enter a description...",
                            default=space.description,
                            input_custom_id="input",
                            long=True,
                            required=False
                        )
                    case "edit_emoji":
                        modal = self.create_modal(
                            title=f"Edit emoji for {space.decorated_name}",
                            custom_id="modal_emoji",
                            label="Space emoji",
                            placeholder="Enter an emoji...",
                            default=space.emoji,
                            input_custom_id="input",
                            required=False
                        )

                if modal:
                    await interaction.response.send_modal(modal)
                else:
                    skip_edit = False

            # Edit modals
            if interaction.custom_id.startswith("modal_"):
                user_input: str | None = interaction.data["components"][0]["components"][0].get("value", None)

                # Obviously this also catches user_input = None, but it's mainly for
                # setting empty strings to None
                if not user_input:
                    user_input = None

                match interaction.custom_id:
                    case "modal_name":
                        space.name = user_input
                    case "modal_description":
                        space.description = user_input
                    case "modal_emoji":
                        if (user_input and emoji.is_emoji(user_input)) or not user_input:
                            space.emoji = user_input
                        else:
                            skip_response = True

def get_cog_type():
    return BeaconConfig

def setup(bot):
    bot.add_cog(BeaconConfig(bot))
