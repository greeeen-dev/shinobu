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
from discord.ext import commands
from stoat.ext import commands as stoat_commands
from shinobu.runtime.models import shinobu_cog
from shinobu.beacon.protocol import beacon
from shinobu.beacon.stoat import driver as stoat_driver
from shinobu.beacon.models import driver as beacon_driver

class StoatBot(stoat_commands.Bot):
    def __init__(self, beacon_obj: beacon.Beacon, driver_obj: stoat_driver.StoatDriver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._beacon: beacon.Beacon = beacon_obj
        self._driver: stoat_driver.StoatDriver = driver_obj

    def register_driver(self):
        if "stoat" not in self._beacon.drivers.platforms:
            self._beacon.drivers.register_driver("stoat", self._driver)

    async def on_ready(self, _, /):
        print(f"Logged in to Stoat as {self.user.name} ({self.user.id})")
        # noinspection PyUnresolvedReferences
        self.register_driver()

class StoatDriverParent(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        # Register cog metadata
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Beacon Stoat driver",
                description="Manages the Beacon driver for Stoat.",
                visible_in_help=True
            )
        )

        # Get Beacon
        self._beacon: beacon.Beacon = self.bot.shared_objects.get("beacon")
        self._driver: stoat_driver.StoatDriver | beacon_driver.BeaconDriver | None = None

        # Create stoat bot attribute
        self.stoat_bot: StoatBot | stoat_commands.Bot | None = None

        # Check if driver is already initialized
        if "stoat" in self._beacon.drivers.platforms:
            self._driver = self._beacon.drivers.get_driver("stoat")
            self.stoat_bot = self._driver.bot
            return

        # Check if we can register Stoat
        self.can_boot: bool = False
        has_whitelist: bool = self._beacon.config.get("enable_platform_whitelist")
        available_platforms: bool = self._beacon.config.get("enabled_platforms")

        if (has_whitelist and "stoat" in available_platforms) or not has_whitelist:
            self.can_boot = True

            # Reserve driver
            self._beacon.drivers.reserve_driver("stoat")

            # Create driver
            self._driver = stoat_driver.StoatDriver(self.stoat_bot, self._beacon.messages)

    async def run_stoat(self, token: str):
        if not self.can_boot:
            print("Stoat not whitelisted in Beacon config. Shutting down Stoat bot parent.")
            return

        while True:
            # noinspection PyBroadException
            try:
                bot_needs_open: bool = (self.stoat_bot is None) or (self.stoat_bot.closed if self.stoat_bot else False)
                if bot_needs_open:
                    # Create new bot
                    self.stoat_bot: StoatBot | stoat_commands.Bot = StoatBot(
                        self._beacon,
                        self._driver,
                        command_prefix=self.bot.command_prefix,
                        token=token
                    )
                    self._driver.replace_bot(self.stoat_bot)

                # Run bot
                # noinspection PyBroadException
                try:
                    await self.stoat_bot.start()
                except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
                    # Exit loop
                    break
                except:
                    traceback.print_exc()
                    print("stoat bot died, restarting in 5 seconds")

                    try:
                        await asyncio.sleep(5)
                    except GeneratorExit:
                        break
                else:
                    # Bot exited gracefully
                    print("Shutting down Stoat bot parent.")
                    break
            except:
                traceback.print_exc()
                print("Stoat bot parent task failed, exiting.")
                break

    @commands.Cog.listener()
    async def on_ready(self):
        # There's already a task for the bot
        if self.bot.shared_objects.get("stoat_task"):
            return

        print("Starting Stoat...")
        token: str = await self.bot.loop.run_in_executor(None, lambda: self._shinobu_secrets.retrieve("TOKEN_STOAT"))

        # Start stoat bot
        task: asyncio.Task = self.bot.loop.create_task(self.run_stoat(token))
        self.bot.shared_objects.add("stoat_task", task)

def get_cog_type():
    return StoatDriverParent

def setup(bot):
    bot.add_cog(StoatDriverParent(bot))
