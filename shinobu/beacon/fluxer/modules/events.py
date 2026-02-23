from fluxer import cog

class FluxerEvents(cog.Cog):
    def __init__(self, bot):
        super().__init__(bot)

    @cog.Cog.listener()
    async def on_ready(self):
        print(f"Logged in to Fluxer as {self.bot.user.username}#{self.bot.user.discriminator} ({self.bot.user.id})")
        # noinspection PyUnresolvedReferences
        self.bot.register_driver()

async def setup(bot):
    await bot.add_cog(FluxerEvents(bot))