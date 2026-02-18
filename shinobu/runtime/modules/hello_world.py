import discord
from discord.ext import bridge, commands
from shinobu.runtime.models import shinobu_cog

class HelloWorld(shinobu_cog.ShinobuCog):
    def __init__(self, bot, **kwargs):
        # Register cog metadata
        self.setup_shinobu_cog(
            bot,
            **kwargs,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Hello World!",
                description="A hello world command!",
                visible_in_help=False
            )
        )

    @bridge.bridge_command(name="hello", description="Hello world!")
    async def hello(self, ctx: bridge.BridgeContext):
        await ctx.respond("Hello world!")

def setup(bot):
    bot.add_cog(HelloWorld(bot))
