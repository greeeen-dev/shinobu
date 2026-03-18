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
from discord.ext import commands, bridge
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon

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

    @bridge.bridge_group(name="config")
    async def config_universal(self, ctx):
        # Universal command group.
        pass

def get_cog_type():
    return BeaconConfig

def setup(bot):
    bot.add_cog(BeaconConfig(bot))
