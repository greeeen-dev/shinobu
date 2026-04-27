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

import stoat
import uuid
from stoat.ext import commands
from shinobu.beacon.stoat.models import embed as stoat_embed
from shinobu.beacon.protocol import beacon, pairing as beacon_pairing
from shinobu.beacon.models import server as beacon_server, driver as beacon_driver

class BeaconPairing(commands.Gear):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

        # Get Beacon
        # noinspection PyUnresolvedReferences
        self._beacon: beacon.Beacon = self.bot.beacon

    @commands.group(name='pairing')
    async def pairing_text(self, ctx):
        pass

    @pairing_text.command(name="pair-server")
    @commands.is_owner()
    async def pair_server(self, ctx: commands.Context, code: str | None = None):
        """Pairs a server with other servers to enable more bridge features."""

        stoat_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("stoat")
        server: beacon_server.BeaconServer = stoat_driver.get_server(ctx.server.id)

        if code:
            # Get pairing code's server
            origin_server: beacon_server.BeaconServer | None = self._beacon.pairing.get_pairing_code_server(code)

            if not origin_server:
                await ctx.send("not a valid pairing code :c", replies=[ctx.message])

            # Revoke pairing code
            self._beacon.pairing.revoke_pairing_code(code)

            # Pair servers
            new_pairing: bool = False

            # Does the server have an existing pairing?
            if server.pairing:
                # Get pairing
                pairing: beacon_pairing.BeaconPairing = self._beacon.pairing.get_pairing(server.pairing)
            elif origin_server.pairing:
                # Get pairing
                pairing: beacon_pairing.BeaconPairing = self._beacon.pairing.get_pairing(origin_server.pairing)
            else:
                # Create new pairing
                pairing: beacon_pairing.BeaconPairing = beacon_pairing.BeaconPairing(str(uuid.uuid4()))
                pairing.add_server(origin_server)
                new_pairing = True

            # Add server to pairing
            pairing.add_server(server)

            # Register pairing if needed
            if new_pairing:
                self._beacon.pairing.add_pairing(pairing)

            embed: stoat_embed.Embed = stoat_embed.Embed(
                title="\U00002705 servers paired!",
                description=f"Your server is now paired with **{len(pairing.servers) - 1}** other server(s).",
                color=self.bot.colors.success
            )
            embed.add_field(
                name="Pairing ID",
                value=pairing.id
            )
            embed.set_footer(
                text="This pairing code is now revoked. To pair more servers, you will need a new pairing code."
            )
            embed_data = await embed.to_dict(self.bot.http.state)

            await ctx.send(embeds=[embed], replies=[ctx.message])
        else:
            # Create pairing code
            code: str = self._beacon.pairing.new_pairing_code(server)

            try:
                embed: stoat_embed.Embed = stoat_embed.Embed(
                    title="your pairing code is here \U0001F440",
                    description=(
                        f"Pairing code: ||`{code}`||\n"+
                        "This code is valid for **30 minutes** to pair **one server**. You will need a new pairing "+
                        "code for each server you want to pair (excluding your own one)."
                    ),
                    color=self.bot.colors.shinobu
                )
                embed.set_footer(
                    text="NOTE: This does not establish a bridge between a paired server."
                )
                print(embed.description)
                await ctx.author.send(embeds=[embed])
            except stoat.HTTPException:
                self._beacon.pairing.revoke_pairing_code(code)
                await ctx.send("couldn't send you a dm, please enable dms! :c", replies=[ctx.message])
            else:
                await ctx.send("pairing code created! check your dms :eyes:", replies=[ctx.message])

async def setup(bot: commands.Bot):
    await bot.add_gear(BeaconPairing(bot))
