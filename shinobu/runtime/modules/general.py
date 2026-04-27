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

import random
import discord
from discord.ext import commands, bridge
from shinobu.runtime.models import shinobu_cog

def cleanup_code(content):
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')

class General(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="General",
                description="General commands",
                visible_in_help=True
            )
        )

    @commands.command(name="nya", aliases=["mrrp", "meow", "miao"])
    async def nya(self, ctx: commands.Context):
        """:333"""

        cat_noises = [
            "meow", "mrrp", "nya", "miao", "purr"
        ]

        await ctx.send(" ".join([random.choice(cat_noises) for _ in range(3)]) + " :333")

    @bridge.bridge_command(name="about")
    async def about(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext):
        """Shows info about the bot."""

        embed: discord.Embed = discord.Embed(
            title=self.bot.user.global_name or self.bot.user.name,
            description="Converse from anywhere, anytime. Powered by [Shinobu](https://github.com/greeeen-dev/shinobu).",
            color=self.bot.colors.shinobu
        )
        embed.set_footer(text=f"Version {self.bot.version} | Made with \u2764\ufe0f by Green (@greeeen-dev)")

        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))
