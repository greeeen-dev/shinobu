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

import random
import uuid
import discord
from functools import partial
from discord.ext import commands, bridge
from shinobu.runtime.models import shinobu_cog, ui_kit

def cleanup_code(content):
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')

class VirtualContext:
    def __init__(self, bot: commands.Bot, author: discord.User, channel: discord.TextChannel, guild: discord.Guild,
                 command: discord.ApplicationCommand | commands.Command):
        self.bot: commands.Bot = bot
        self.author: discord.User = author
        self.channel: discord.TextChannel = channel
        self.guild: discord.Guild = guild
        self.command: discord.ApplicationCommand | commands.Command = command

class General(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="General",
                description="General commands",
                emoji="\U00002764\U0000FE0F",
                visible_in_help=True
            )
        )

    @bridge.bridge_command(name="nya")
    async def nya(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext):
        """:333"""

        cat_noises = [
            "meow", "mrrp", "nya", "miao", "purr"
        ]

        await ctx.respond(" ".join([random.choice(cat_noises) for _ in range(3)]) + " :333")

    @bridge.bridge_command(name="about")
    async def about(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext):
        """Shows info about the bot."""

        embed: discord.Embed = discord.Embed(
            title=self.bot.user.global_name or self.bot.user.name,
            description="Converse from anywhere, anytime. Powered by [Shinobu](https://github.com/greeeen-dev/shinobu).",
            color=self.bot.colors.shinobu
        )
        embed.set_footer(text=f"Version {self.bot.version} | Made with \u2764\ufe0f by Green (@greeeen-dev)")

        await ctx.respond(embed=embed)

    @staticmethod
    def get_group_commands(command_group: discord.SlashCommandGroup | bridge.BridgeCommandGroup
                           ) -> list[discord.ApplicationCommand | bridge.BridgeCommand]:
        final_commands: list[discord.ApplicationCommand | bridge.BridgeCommand] = []

        for cmd in command_group.walk_commands():
            if isinstance(command_group, bridge.BridgeCommandGroup) and isinstance(cmd, commands.Command):
                continue

            final_commands.append(cmd)

        return final_commands

    @staticmethod
    def get_slash_signature(slash_command: discord.SlashCommand):
        options_text: list[str] = []

        type_mapping: dict[discord.SlashCommandOptionType, str] = {
            discord.SlashCommandOptionType.string: "string",
            discord.SlashCommandOptionType.integer: "integer",
            discord.SlashCommandOptionType.boolean: "boolean",
            discord.SlashCommandOptionType.user: "user",
            discord.SlashCommandOptionType.channel: "channel",
            discord.SlashCommandOptionType.role: "role",
            discord.SlashCommandOptionType.mentionable: "mentionable",
            discord.SlashCommandOptionType.number: "number",
            discord.SlashCommandOptionType.attachment: "attachment"
        }

        for option in slash_command.options:
            if option.required:
                options_text.append(f"<{option.name}: {type_mapping.get(option.input_type, 'unknown')}>")
            else:
                options_text.append(f"[{option.name}: {type_mapping.get(option.input_type, 'unknown')}]")

        return f"/{slash_command.qualified_name} " + " ".join(options_text)

    async def get_help_view(self,
                            ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext | discord.AutocompleteContext
                            ) -> ui_kit.ShinobuListDiscordView:
        # Create new list UI
        list_ui: ui_kit.ShinobuListDiscordView = ui_kit.ShinobuListDiscordView(
            ":keyboard: shinobu help",
            "Select a cog or search a command to get started!",
            self.bot.colors.shinobu,
            display_id=False
        )

        virtual_context: VirtualContext | None = None

        if isinstance(ctx, discord.AutocompleteContext):
            # Override context
            author: discord.User = ctx.interaction.user
            virtual_context = VirtualContext(
                bot=self.bot,
                author=ctx.interaction.user,
                guild=ctx.interaction.guild,
                channel=ctx.interaction.channel,
                command=ctx.command
            )
        else:
            author: discord.User = ctx.author

        # Add spaces
        for cog_id, cog_object in self.bot.cogs.items():
            if not isinstance(cog_object, shinobu_cog.ShinobuCog):
                # We can't index this cog
                continue

            if not cog_object.shinobu_metadata.visible_in_help:
                continue

            if (
                    cog_object.shinobu_metadata.owner_only and
                    not author.id == self.bot.owner_id and
                    not author.id in self.bot.owner_ids
            ):
                continue

            cog_name: str = cog_object.shinobu_metadata.name
            cog_emoji: str = cog_object.shinobu_metadata.emoji
            cog_description: str = cog_object.shinobu_metadata.description

            cog_commands: list[
                discord.SlashCommand | bridge.BridgeCommand | commands.Command |
                discord.SlashCommandGroup | bridge.BridgeCommandGroup | commands.Group
                ] = cog_object.get_commands()

            cog_final_commands: list[discord.SlashCommand | bridge.BridgeCommand | commands.Command] = []

            for cog_command in cog_commands:
                if (
                        isinstance(cog_command, discord.SlashCommandGroup) or
                        isinstance(cog_command, bridge.BridgeCommandGroup) or
                        isinstance(cog_command, commands.Group)
                ) and not (
                        isinstance(cog_command, bridge.BridgeExtGroup) or
                        isinstance(cog_command, bridge.BridgeSlashGroup)
                ):
                    cog_final_commands = cog_final_commands + self.get_group_commands(cog_command)
                elif (
                        isinstance(cog_command, discord.SlashCommand) or
                        isinstance(cog_command, bridge.BridgeCommand)
                ) and not (
                        isinstance(cog_command, bridge.BridgeSlashCommand) or
                        isinstance(cog_command, bridge.BridgeExtCommand)
                ):
                    cog_final_commands.append(cog_command)
                elif (
                        isinstance(cog_command, commands.Command)
                ) and not (
                        isinstance(cog_command, bridge.BridgeExtCommand)
                ):
                    cog_final_commands.append(cog_command)

            entry: ui_kit.ShinobuListEntry = ui_kit.ShinobuListEntry(
                entry_id=cog_id,
                name=cog_name,
                description=cog_description,
                emoji=cog_emoji,
                indexable=False
            )

            for final_command in cog_final_commands:
                is_universal: bool = False
                is_slash: bool = False
                can_run: bool = False

                if isinstance(final_command, bridge.BridgeCommand):
                    is_universal = True
                    is_slash = True
                    command_mention: str = final_command.slash_variant.mention
                    command_plaintext_mention: str = f"/{final_command.slash_variant.qualified_name}"
                    command_description: str = final_command.slash_variant.description

                    try:
                        can_run = await final_command.slash_variant.can_run(virtual_context or ctx)
                    except commands.CommandError as e:
                        pass
                elif isinstance(final_command, discord.SlashCommand):
                    is_slash = True
                    command_mention: str = final_command.mention
                    command_plaintext_mention: str = f"/{final_command.qualified_name}"
                    command_description: str = final_command.description

                    try:
                        can_run = await final_command.can_run(virtual_context or ctx)
                    except commands.CommandError:
                        pass
                else:
                    command_mention: str = f"`{self.bot.command_prefix}{final_command.qualified_name}`"
                    command_plaintext_mention: str = f"{self.bot.command_prefix}{final_command.qualified_name}"
                    command_description: str = final_command.description

                    try:
                        can_run = await final_command.can_run(virtual_context or ctx)
                    except commands.CommandError:
                        pass

                cmd_entry: ui_kit.ShinobuListEntry = ui_kit.ShinobuListEntry(
                    entry_id=str(uuid.uuid4()),
                    name=command_mention,
                    plaintext_name=command_plaintext_mention,
                    description=command_description,
                    emoji="\U00002728" if is_universal else None,
                    hidden=not can_run
                )

                if is_universal:
                    cmd_entry.add_field(
                        name=":sparkles: Universal Command",
                        value="This is a Universal Command! It can be used as both slash and text commands."
                    )

                if is_universal or is_slash:
                    if is_universal:
                        signature: str = self.get_slash_signature(final_command.slash_variant)
                    else:
                        signature: str = self.get_slash_signature(final_command)

                    cmd_entry.add_field(name="Usage (slash)", value=f"`{signature.rstrip()}`")
                if is_universal or not is_slash:
                    if is_universal:
                        command_name: str = final_command.ext_variant.qualified_name
                        command_signature: str = final_command.ext_variant.signature
                    else:
                        command_name: str = final_command.qualified_name
                        command_signature: str = final_command.signature

                    if command_signature == "<ctx>":
                        command_signature = ""
                    elif command_signature.startswith("<ctx> "):
                        command_signature = command_signature.replace("<ctx> ", "", 1)

                    signature: str = (
                        f"{self.bot.command_prefix}{command_name} {command_signature}"
                    )

                    cmd_entry.add_field(name="Usage (text)", value=f"`{signature.rstrip()}`")

                entry.add_child(cmd_entry)

            list_ui.add_entry(entry)

        return list_ui

    async def help_autocomplete(self, ctx: discord.AutocompleteContext) -> list[discord.OptionChoice]:
        priority_matches: list[str] = []
        matches: list[str] = []
        list_ui: ui_kit.ShinobuListDiscordView = await self.get_help_view(ctx)
        list_ui.map_all_entries()

        for command in list_ui.all_entries:
            if command.hidden or not command.indexable:
                continue

            compare_name: str = command.plaintext_name.lower()
            if compare_name.startswith("/"):
                compare_name = compare_name.replace("/", "", 1)
            elif compare_name.startswith(self.bot.command_prefix):
                compare_name = compare_name.replace(self.bot.command_prefix, "", 1)

            if (
                    command.plaintext_name.lower().startswith(ctx.value.lower()) or
                    compare_name.lower().startswith(ctx.value.lower())
            ):
                priority_matches.append(command.plaintext_name)
            elif ctx.value.lower() in command.name.lower():
                matches.append(command.plaintext_name)
            elif len(ctx.value) == 0:
                matches.append(command.plaintext_name)

        all_matches: list[str] = (priority_matches + matches)[:25]

        if len(ctx.value) > 0:
            if len(all_matches) == 25:
                all_matches.pop(-1)

            all_matches.append(f"\U0001F50D {ctx.value}")

        return [
            discord.OptionChoice(name=match) for match in all_matches
        ]

    @bridge.bridge_command(name="help")
    @bridge.bridge_option("query", description="The search query. Leave empty to list all commands.",
                          autocomplete=partial(help_autocomplete))
    async def help(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext, query: str | None = None):
        """Shows bot help."""

        list_ui: ui_kit.ShinobuListDiscordView = await self.get_help_view(ctx)

        # Run loop
        await list_ui.run(self.bot, ctx, query=query)

def setup(bot):
    bot.add_cog(General(bot))
