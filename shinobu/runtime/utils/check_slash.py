from discord.ext import bridge

def is_slash(ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext):
    return isinstance(ctx, bridge.BridgeApplicationContext)