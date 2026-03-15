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

from discord.ext import commands
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon

class BeaconManager(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Beacon Manager",
                description="A module containing commands for managing Beacon.",
                emoji="\U00002699\U0000FE0F",
                visible_in_help=True
            )
        )

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")

    @commands.group(name='beacon')
    async def beacon_text(self, ctx):
        pass

    @beacon_text.command(name="bacon")
    async def bacon(self, ctx: commands.Context):
        """Bacon 🥓"""
        await ctx.send("Bacon :bacon:")

    @beacon_text.command(name="enable-platform")
    @commands.is_owner()
    async def enable_platform(self, ctx: commands.Context, platform: str):
        """Enables a Beacon platform."""

        try:
            self._beacon.enable_platform(platform)
        except ValueError:
            return await ctx.send(f"platform {platform} unavailable or already enabled")
        await ctx.send(f"enabled platform {platform}")

    @beacon_text.command(name="disable-platform")
    @commands.is_owner()
    async def disable_platform(self, ctx: commands.Context, platform: str):
        """Disables a Beacon platform."""

        try:
            self._beacon.disable_platform(platform)
        except ValueError:
            return await ctx.send(f"platform {platform} unavailable or already disabled")
        await ctx.send(f"disabled platform {platform}")

def get_cog_type():
    return BeaconManager

def setup(bot):
    bot.add_cog(BeaconManager(bot))
