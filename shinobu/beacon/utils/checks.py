import discord
from discord.ext import bridge, commands
from shinobu.beacon.protocol import beacon as beacon_protocol

def get_beacon(bot) -> beacon_protocol.Beacon:
    return bot.shared_objects.get("beacon")

def get_user(ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext) -> discord.User:
    if isinstance(ctx, bridge.BridgeApplicationContext):
        return ctx.user
    else:
        return ctx.author

class CommandChecks:
    @staticmethod
    def is_admin():
        async def predicate(ctx):
            beacon: beacon_protocol.Beacon = get_beacon(ctx.bot)
            return beacon.moderators.is_admin(str(get_user(ctx).id))

        return commands.check(predicate)

    @staticmethod
    def is_moderator():
        async def predicate(ctx):
            beacon: beacon_protocol.Beacon = get_beacon(ctx.bot)
            return beacon.moderators.is_moderator(str(get_user(ctx).id))

        return commands.check(predicate)