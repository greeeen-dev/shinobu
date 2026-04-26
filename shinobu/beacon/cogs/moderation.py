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
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.models import message as beacon_message
from shinobu.beacon.utils.checks import CommandChecks

class BeaconModeration(shinobu_cog.ShinobuCog):
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

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")

    @bridge.bridge_group(name='moderation')
    async def moderation_universal(self, ctx):
        pass

    @commands.message_command(name="Message properties")
    @CommandChecks.can_check_details()
    async def properties(self, ctx: discord.ApplicationContext, message: discord.Message):
        # Get message
        message_obj: beacon_message.BeaconMessage = self._beacon.messages.get_message(str(message.id))

        if not message_obj:
            return await ctx.respond("could not get message :c", ephemeral=True)

        # Get message info
        info: str = message_obj.readable_info()

        await ctx.respond(content=f"Message info for `{message.id}`\n```\n{info}\n```", ephemeral=True)

def get_cog_type():
    return BeaconModeration

def setup(bot):
    bot.add_cog(BeaconModeration(bot))
