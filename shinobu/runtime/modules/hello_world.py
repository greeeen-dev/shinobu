import traceback
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
    async def hello(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext):
        await ctx.respond("Hello world!")

    @commands.command(name="secrets-test", description="Tests fine-grained secrets and files access")
    async def secrets_test(self, ctx: commands.Context):
        test_pass = True

        # Test 1: Check secrets access
        try:
            self._shinobu_secrets.retrieve("NOT_A_SECRET")
        except:
            traceback.print_exc()
            test_pass = False

        # Test 2: Check fine-grained access enforcement (this should error)
        try:
            self._shinobu_secrets.retrieve("TOKEN")
            test_pass = False
        except ValueError:
            pass

        # Test 3: Read from file
        try:
            contents = self._shinobu_files.read("testfile")
            print(f'File contents: {contents}')
        except:
            traceback.print_exc()
            test_pass = False

        # Test 4: Write to file
        try:
            self._shinobu_files.save("testfile", "hi :3")
        except:
            traceback.print_exc()
            test_pass = False

        await ctx.send(f"Test result: `{test_pass}`", reference=ctx.message)

def get_cog_type():
    return HelloWorld

def setup(bot):
    bot.add_cog(HelloWorld(bot))
