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

import discord
from discord.ext import bridge, commands
from shinobu.runtime.models import shinobu_cog, errors
from shinobu.beacon.models import message as beacon_message, space as beacon_space, beacon_cog
from shinobu.beacon.utils.checks import CommandChecks

class BeaconModeration(beacon_cog.BeaconCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Moderation",
                description="A module containing commands for bridge moderation.",
                emoji="\U0001F6E1\U0000FE0F",
                visible_in_help=True
            )
        )

    @bridge.bridge_group(name='moderation', contexts={discord.InteractionContextType.guild})
    async def moderation_universal(self, ctx):
        pass

    @commands.message_command(name="Message properties", contexts={discord.InteractionContextType.guild})
    @CommandChecks.can_check_details()
    async def properties(self, ctx: discord.ApplicationContext, message: discord.Message):
        # Get message
        message_obj: beacon_message.BeaconMessage = self._beacon.messages.get_message(str(message.id))

        if not message_obj:
            return await ctx.respond("could not get message :c", ephemeral=True)

        # Get message info
        info: str = message_obj.readable_info()

        await ctx.respond(content=f"Message info for `{message.id}`\n```\n{info}\n```", ephemeral=True)

    @moderation_universal.command(name="kick")
    @bridge.bridge_option("target", description="The target ID. This may be a server ID from any platform.")
    @bridge.bridge_option("space_id", description="The Space ID. Leave empty to use the Space linked to this channel.")
    @CommandChecks.can_manage()
    async def kick(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext,
                   target: str, space_id: str | None = None):
        """Kicks a server from a Space."""
        space: beacon_space.BeaconSpace = self.autodetect(ctx.channel, space_id)

        if not self.can_manage(space, ctx.guild.id, user_id=ctx.author.id):
            raise commands.CheckFailure()

        # Get server
        member: (
            beacon_space.BeaconSpaceMember | beacon_space.BeaconPartialSpaceMember | None
        ) = space.get_member(target)

        if not member:
            member = space.get_partial_member(target)
            if not member:
                raise errors.ShinobuNotFound("target")

        # Kick member
        space.leave(member or target)

        await ctx.respond(
            f"kicked **{member.server.name if isinstance(member, beacon_space.BeaconSpaceMember) else target}** >:<"
        )

    @moderation_universal.command(name="ban")
    @bridge.bridge_option("target", description="The target ID. This may be a server or user ID from any platform.")
    @bridge.bridge_option("space_id", description="The Space ID. Leave empty to use the Space linked to this channel.")
    @CommandChecks.can_manage()
    async def ban(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext,
                   target: str, space_id: str | None = None):
        """Bans a server or user from a Space. Banned servers or users cannot rejoin a Space."""
        space: beacon_space.BeaconSpace = self.autodetect(ctx.channel, space_id)

        if not self.can_manage(space, ctx.guild.id, user_id=ctx.author.id):
            raise commands.CheckFailure()

        # Get server
        member: beacon_space.BeaconSpaceMember | None = space.get_member(target)

        # Ban member (or target ID)
        space.ban(member or target)

        await ctx.respond(f"banned **{member.server.name if member else target}** >:<")

    @moderation_universal.command(name="unban")
    @bridge.bridge_option("target", description="The target ID. This may be a server or user ID from any platform.")
    @bridge.bridge_option("space_id", description="The Space ID. Leave empty to use the Space linked to this channel.")
    @CommandChecks.can_manage()
    async def unban(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext,
                    target: str, space_id: str | None = None):
        """Unbans a server or user from a Space."""
        space: beacon_space.BeaconSpace = self.autodetect(ctx.channel, space_id)

        if not self.can_manage(space, ctx.guild.id, user_id=ctx.author.id):
            raise commands.CheckFailure()

        # Unban target
        space.unban(target)

        await ctx.respond(f"unbanned **{target}** :D")

def get_cog_type():
    return BeaconModeration

def setup(bot):
    bot.add_cog(BeaconModeration(bot))
