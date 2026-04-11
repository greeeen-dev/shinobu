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

import uuid
import traceback
import discord
from discord.ext import commands, bridge
from shinobu.runtime.models.colors import Colors
from shinobu.runtime.utils import check_slash

from shinobu.runtime.models import shinobu_cog

class ShinobuEvents(shinobu_cog.ShinobuCog):
    def __init__(self, bot, **kwargs):
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Events",
                description="A cog handling Shinobu bot events.",
                visible_in_help=False
            )
        )
        self.expected_errors: list = [
            commands.CheckFailure
        ]

    def check_error_expected(self, error):
        for expected in self.expected_errors:
            if isinstance(error, expected):
                return True

        return False

    async def handle_error(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext |
                                      discord.ApplicationContext | commands.Context,
                           error):
        is_slash: bool = check_slash.is_slash(ctx)
        traceback_str: str = "".join(traceback.format_exception(error))
        error_id: str = str(uuid.uuid4())
        record_error: bool = False
        error_title: str = "oh nooooo >.<"
        error_description: str = "An error occurred and the command failed to run. Sorry about that... :<"

        # Handle expected errors
        if isinstance(error, commands.CheckFailure):
            error_title = "nu >:c"
            error_description = "You don't have the right permissions to run this command."
        else:
            # Unexpected error
            record_error = True

        embed: discord.Embed = discord.Embed(
            title=error_title,
            description=error_description,
            color=Colors.error
        )

        if record_error:
            # Record error
            error_data: dict[str, int] = {
                "server": ctx.guild.id,
                "channel": ctx.channel.id,
                "user": ctx.author.id
            }
            self.bot.errors.add(error_id, traceback_str, error_data)

            # Add error UUID
            embed.add_field(
                name="Error UUID",
                value=f"`{error_id}`"
            )
            embed.set_footer(text="Send the error UUID to this instance's owner for assistance.")

        if is_slash and not ctx.interaction.response.is_done():
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Shinobu Runtime is ready! :3")
        print(f"Logged in as {self.bot.user.name}#{self.bot.user.discriminator} ({self.bot.user.id})")

        # Handle restart
        if self.bot.restart_message_id:
            channel: discord.TextChannel | None = self.bot.get_channel(self.bot.restart_message_channel_id)
            if not channel:
                return

            message: discord.PartialMessage = discord.PartialMessage(channel=channel, id=self.bot.restart_message_id)
            await message.edit(content="bot restarted! :white_check_mark:")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not self.check_error_expected(error):
            traceback.print_exc(error)

        await self.handle_error(ctx, error)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if not self.check_error_expected(error):
            traceback.print_exc(error)

        await self.handle_error(ctx, error)

def setup(bot):
    bot.add_cog(ShinobuEvents(bot))
