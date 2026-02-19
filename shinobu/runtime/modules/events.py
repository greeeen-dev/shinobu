import discord
from discord.ext import commands
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

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready, woohoo!")
        print(f"Logged in as {self.bot.user.name}#{self.bot.user.discriminator} ({self.bot.user.id})")

def setup(bot):
    bot.add_cog(ShinobuEvents(bot))
