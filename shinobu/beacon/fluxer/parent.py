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
import traceback
import fluxer
from discord.ext import commands
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.fluxer import driver as fluxer_driver
from shinobu.beacon.models import driver as beacon_driver

class FluxerBot(fluxer.Bot):
    def __init__(self, beacon_obj: beacon.Beacon, driver_obj: fluxer_driver.FluxerDriver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._beacon: beacon.Beacon = beacon_obj
        self._driver: fluxer_driver.FluxerDriver = driver_obj

    def register_driver(self):
        self._beacon.drivers.register_driver("fluxer", self._driver)

class FluxerDriverParent(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Beacon Fluxer driver",
                description="Manages the Beacon driver for Fluxer.",
                visible_in_help=True
            )
        )

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")
        self._driver: fluxer_driver.FluxerDriver | beacon_driver.BeaconDriver | None = None

        # Create Fluxer bot attribute
        self.fluxer_bot: FluxerBot | fluxer.Bot | None = None

        # Check if driver is already initialized
        if "fluxer" in self._beacon.drivers.platforms:
            self._driver = self._beacon.drivers.get_driver("fluxer")
            self.fluxer_bot = self._driver.bot
            return

        # Reserve driver
        self._beacon.drivers.reserve_driver("fluxer")

        # Create driver
        self._driver = fluxer_driver.FluxerDriver(self.fluxer_bot, self._beacon.messages)

    async def run_fluxer(self, token: str):
        while True:
            # noinspection PyBroadException
            try:
                bot_needs_open: bool = (self.fluxer_bot is None) or (self.fluxer_bot.closed if self.fluxer_bot else False)
                if bot_needs_open:
                    # Create new bot
                    self.fluxer_bot: FluxerBot | fluxer.Bot = FluxerBot(
                        self._beacon,
                        self._driver,
                        command_prefix=self.bot.command_prefix
                    )
                    self._driver.replace_bot(self.fluxer_bot)

                # Load events cog
                await self.fluxer_bot.load_extension("shinobu.beacon.fluxer.modules.events")

                # Run bot
                # noinspection PyBroadException
                try:
                    await self.fluxer_bot.start(token)
                except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
                    # Exit loop
                    break
                except:
                    traceback.print_exc()
                    print("fluxer bot died, restarting in 5 seconds")

                    try:
                        await asyncio.sleep(5)
                    except GeneratorExit:
                        break
                else:
                    # Bot exited gracefully
                    print("Shutting down Fluxer bot parent.")
                    break
            except:
                traceback.print_exc()
                print("Fluxer bot parent task failed, exiting.")
                break

    @commands.Cog.listener()
    async def on_ready(self):
        # There's already a task for the bot
        if self.bot.shared_objects.get("fluxer_task"):
            return

        print("Starting Fluxer client...")
        token: str = await self.bot.loop.run_in_executor(None, lambda: self._shinobu_secrets.retrieve("TOKEN_FLUXER"))

        # Start Fluxer bot
        task: asyncio.Task = self.bot.loop.create_task(self.run_fluxer(token))
        self.bot.shared_objects.add("fluxer_task", task)

def get_cog_type():
    return FluxerDriverParent

def setup(bot):
    bot.add_cog(FluxerDriverParent(bot))
