import inspect
import io
import textwrap
import time
import traceback
import base64
from contextlib import redirect_stdout
from discord.ext import commands
from shinobu.runtime.models import shinobu_cog


def cleanup_code(content):
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')

def is_owner(ctx):
    print(ctx.message.author)
    return ctx.message.author.id == 356456393491873795

class Admin(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Admin",
                description="Admin commands",
                visible_in_help=True
            )
        )

    @commands.command(name="eval", description="Evaluates code.")
    @commands.is_owner()
    async def eval(self, ctx: commands.Context, *, body: str):
        env = {
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'source': inspect.getsource,
            'bot': self.bot
        }

        # Run cleanup
        body = cleanup_code(body)

        # Add other globals
        env.update(globals())

        # Set up stdout
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        # Convert method string to function
        try:
            if 'bot.token' in body or 'dotenv' in body or '.env' in body or 'environ' in body or 'tokenstore' in body:
                return await ctx.send(f':x: Phrase blocked.', reference=ctx.message)
            exec(to_compile, env)
        except:
            pass

        # Check if the function was generated successfully
        if 'func' not in env:
            return await ctx.send(':x: Could not run code. This may be due to a syntax error.', reference=ctx.message)

        # Safely generate first few characters
        # This is used to ensure the token is not in the output
        token_start = base64.b64encode(bytes(str(self.bot.user.id), 'utf-8')).decode('utf-8')

        # Get start time
        tstart = time.time()

        try:
            with redirect_stdout(stdout):
                # noinspection PyUnresolvedReferences
                await env['func']()
        except:
            # Get error output
            value = await self.bot.loop.run_in_executor(None, lambda: stdout.getvalue())
            await ctx.send(':x: An error occurred while executing the code.', reference=ctx.message)

            # Ensure token is not in output
            if token_start in value:
                return await ctx.author.send(':x: Phrase blocked.')

            # DM eval result
            await ctx.author.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            # Get total eval time
            exec_time = round(time.time() - tstart, 4)

            # Get output
            value = await self.bot.loop.run_in_executor(None, lambda: stdout.getvalue())

            # Ensure token is not in output
            if token_start in value:
                return await ctx.send(':x: Phrase blocked.')

            # Show result
            if value == '':
                await ctx.send(f':white_check_mark: Evaluation completed in `{exec_time}` seconds.')
            else:
                await ctx.send(f':white_check_mark: Evaluation completed in `{exec_time}` seconds.\n```\n{value}\n```')

def setup(bot):
    bot.add_cog(Admin(bot))
