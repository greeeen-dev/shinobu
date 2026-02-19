from discord.ext import commands
from shinobu.runtime.models import shinobu_cog

class BeaconBackend(shinobu_cog.ShinobuCog):
    def __init__(self, bot, **kwargs):
        # Register cog metadata
        self.setup_shinobu_cog(
            bot,
            **kwargs,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Beacon Backend",
                description="Manages the Shinobu Beacon bridge protocol.",
                visible_in_help=True
            )
        )

    def on_entitlements_issued(self):
        # We will initialize Beacon here
        self.bot.shared_objects.add("beacon")
        return

def get_cog_type():
    return BeaconBackend

def setup(bot):
    bot.add_cog(BeaconBackend(bot))
