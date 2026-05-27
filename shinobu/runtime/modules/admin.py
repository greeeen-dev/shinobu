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

import inspect
import io
import textwrap
import time
import traceback
import base64
import discord
from contextlib import redirect_stdout
from discord.ext import commands
from shinobu.runtime.models import shinobu_cog

def cleanup_code(content):
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')

class Admin(shinobu_cog.ShinobuCog):
    def __init__(self, bot):
        super().__init__(
            bot,
            shinobu_metadata=shinobu_cog.ShinobuCogMetadata(
                name="Admin",
                description="Admin commands",
                emoji="\U0001F9F0",
                visible_in_help=True,
                owner_only=True
            )
        )

    @commands.command(name="eval", description="Evaluates code.")
    @commands.is_owner()
    async def eval(self, ctx: commands.Context, *, body: str):
        """Evaluates code."""

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

    @commands.command(name="view-error", description="Shows info about an error.")
    @commands.is_owner()
    async def view_error(self, ctx: commands.Context, error_id: str):
        """Shows info about an error."""

        error_data: dict | None = self.bot.errors.get(error_id)

        if not error_data:
            return await ctx.reply("could not find this error :/")

        error_metadata: dict = error_data.get("data")
        error_traceback: str = error_data.get("traceback")

        embed = discord.Embed(
            title=f":beetle: error info for {error_id}",
            description=f"```\n{error_traceback}\n```" if error_traceback else "*No traceback recorded. Strange.*",
            color=self.bot.colors.warning
        )
        embed.add_field(
            name="Platform",
            value=error_metadata.get("platform") or "*No platform info recorded*",
            inline=False
        )
        embed.add_field(
            name="Server ID",
            value=error_metadata.get("server") or "*No server ID recorded*",
            inline=False
        )
        embed.add_field(
            name="Channel ID",
            value=error_metadata.get("channel") or "*No channel ID recorded*",
            inline=False
        )
        embed.add_field(
            name="User ID",
            value=error_metadata.get("user") or "*No user ID recorded*",
            inline=False
        )
        embed.set_footer(
            text="This may contain sensitive data. Do not share this with others unless you know what you're doing."
        )

        await ctx.author.send(embed=embed)

        if ctx.guild:
            await ctx.reply("check your dms :eyes:")

    @commands.command(name="throw-error", description="Throws an error. But cutely. That's about it.")
    @commands.is_owner()
    async def throw_error(self, ctx: commands.Context):
        """Throws an error. But cutely. That's about it."""
        raise RuntimeError("haiiiii!!! >w<")

    @commands.command(name="shutdown", aliases=["poweroff"], description="Shuts the bot down.")
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """Shuts the bot down."""
        await ctx.reply("shutting down :zzz:")

        # Shut down bot
        await self.bot.close()

    @commands.command(name="restart", aliases=["reboot"], description="Restarts the bot.")
    @commands.is_owner()
    async def restart(self, ctx: commands.Context):
        """Restarts the bot."""

        # NOTE: This does NOT update Runtime or Beacon.
        # To update them, fully shut down the bot then start it again.

        message: discord.Message = await ctx.reply("restarting :arrows_counterclockwise:")

        # Request restart then shut down bot
        self.bot.request_restart(message=message)
        await self.bot.close()

def setup(bot):
    bot.add_cog(Admin(bot))
