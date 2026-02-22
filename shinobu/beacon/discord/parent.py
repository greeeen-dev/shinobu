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

from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.discord import driver

class DiscordDriverParent(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Beacon Discord driver",
                description="Manages the Beacon driver for Discord.",
                visible_in_help=True
            )
        )

        # Get Beacon
        self.beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")

        # Check if driver is already initialized
        if "discord" in self.beacon.drivers:
            return

        # Register driver
        self.beacon.drivers.register_driver("discord", driver.DiscordDriver(
            self.bot, self.beacon.messages
        ))

def get_cog_type():
    return DiscordDriverParent

def setup(bot):
    bot.add_cog(DiscordDriverParent(bot))
