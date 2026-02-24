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

class BeaconBackend(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Beacon Backend",
                description="Manages the Shinobu Beacon bridge protocol.",
                visible_in_help=True
            )
        )
        self._beacon: beacon.Beacon | None = None

    def on_entitlements_issued(self):
        # We will initialize Beacon here
        if self.bot.shared_objects.get("beacon"):
            # Beacon already initialized
            return

        self._beacon = beacon.Beacon(self.bot, self._shinobu_files, config=self.bot.config.get("beacon"))
        self.bot.shared_objects.add("beacon", self._beacon)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._beacon.initialized:
            self._beacon.load_data()

def get_cog_type():
    return BeaconBackend

def setup(bot):
    bot.add_cog(BeaconBackend(bot))
