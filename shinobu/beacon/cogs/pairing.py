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
import uuid
from discord.ext import bridge
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.utils.checks import CommandChecks
from shinobu.beacon.protocol import beacon, pairing as beacon_pairing
from shinobu.beacon.models import server as beacon_server, driver as beacon_driver

class BeaconPairing(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Pairing",
                description="A module containing server pairing commands.",
                emoji="\U0001F4E1",
                visible_in_help=True
            )
        )

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")

    @bridge.bridge_group(name="pairing")
    async def pairing_universal(self, ctx):
        # Universal command group.
        pass

    @pairing_universal.command(name="pair-server")
    @CommandChecks.can_manage()
    async def pair_server(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext,
                          code: str | None = None):
        """Pairs a server with other servers to enable more bridge features."""

        discord_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")
        server: beacon_server.BeaconServer = discord_driver.get_server(str(ctx.guild.id))

        if code:
            # Get pairing code's server
            pair_server: beacon_server.BeaconServer | None = self._beacon.pairing.get_pairing_code_server(code)

            if not pair_server:
                if isinstance(ctx, bridge.BridgeApplicationContext):
                    await ctx.response.send_message("not a valid pairing code :c", ephemeral=True)
                else:
                    await ctx.respond("not a valid pairing code :c")
                return

            # Revoke pairing code
            self._beacon.pairing.revoke_pairing_code(code)

            # Pair servers
            new_pairing: bool = False

            # Does the server have an existing pairing?
            if server.pairing:
                # Get pairing
                pairing: beacon_pairing.BeaconPairing = self._beacon.pairing.get_pairing(server.pairing)
            else:
                # Create new pairing
                pairing: beacon_pairing.BeaconPairing = beacon_pairing.BeaconPairing(str(uuid.uuid4()))
                pairing.add_server(pair_server)
                new_pairing = True

            # Add server to pairing
            pairing.add_server(server)

            # Register pairing if needed
            if new_pairing:
                self._beacon.pairing.add_pairing(pairing)

            embed: discord.Embed = discord.Embed(
                title=":white_check_mark: servers paired!",
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

            await ctx.respond(embed=embed)
            await self.bot.loop.run_in_executor(None, self._beacon.save_data)
        else:
            # Create pairing code
            code: str = self._beacon.pairing.new_pairing_code(server)

            try:
                embed: discord.Embed = discord.Embed(
                    title="your pairing code is here :eyes:",
                    description=(
                        f"Pairing code: ||`{code}`||\n"+
                        "This code is valid for **30 minutes** to pair **one server**. You will need a new pairing "+
                        "code for each server you want to pair (excluding your own one)."
                    ),
                    color=self.bot.colors.shinobu
                )
                await ctx.author.send(embed=embed)
            except discord.HTTPException:
                self._beacon.pairing.revoke_pairing_code(code)
                if isinstance(ctx, bridge.BridgeApplicationContext):
                    await ctx.response.send_message("couldn't send you a dm, please enable dms! :c", ephemeral=True)
                else:
                    await ctx.respond("couldn't send you a dm, please enable dms! :c")
            else:
                await ctx.respond("pairing code created! check your dms :eyes:")

    @pairing_universal.command(name="unpair-server")
    @CommandChecks.can_manage()
    async def unpair_server(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext):
        """Unpairs a server from its current pairing."""

        discord_driver: beacon_driver.BeaconDriver = self._beacon.drivers.get_driver("discord")
        server: beacon_server.BeaconServer = discord_driver.get_server(str(ctx.guild.id))

        if not server.pairing:
            if isinstance(ctx, bridge.BridgeApplicationContext):
                await ctx.response.send_message("your server isn't paired :/", ephemeral=True)
            else:
                await ctx.respond("your server isn't paired :/")
            return

        pairing: beacon_pairing.BeaconPairing = self._beacon.pairing.get_pairing(server.pairing)
        pairing.remove_server(server)

        embed: discord.Embed = discord.Embed(
            title=":white_check_mark: server unpaired!",
            description=f"Your server is no longer paired with Pairing `{pairing.id}`.",
            color=self.bot.colors.success
        )
        await ctx.respond(embed=embed)
        await self.bot.loop.run_in_executor(None, self._beacon.save_data)

def get_cog_type():
    return BeaconPairing

def setup(bot):
    bot.add_cog(BeaconPairing(bot))
