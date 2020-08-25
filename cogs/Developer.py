import contextlib
import io
import json
import textwrap
import traceback

import discord
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.ext.commands import is_owner

from utils import utils


# noinspection PyBroadException
class Developer(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self._last_result = None
        self.bot = bot

    @staticmethod
    def _cleanup_code(content):
        """Automatically removes code blocks from the code."""

        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            if content[-4] == '\n':
                return '\n'.join(content.split('\n')[1:-1])
            return '\n'.join(content.split('\n')[1:]).rstrip('`')

        # remove `foo`
        return content.strip('` \n')

    @command()
    @is_owner()
    async def kill(self, ctx):
        try:
            self.bot.clear()
            await self.bot.close()
        except Exception as e:
            await ctx.send("Couldn't kill the bot for some reason, maybe this will help:\n" +
                           f"{type(e).__name__} - {e}")

    @command()
    @is_owner()
    async def shard_recon(self, ctx, shard_id: int):
        try:
            self.bot.get_shard(shard_id).reconnect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")
    
    @command()
    @is_owner()
    async def shard_discon(self, ctx, shard_id: int):
        try:
            self.bot.get_shard(shard_id).disconnect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")
    
    @command()
    @is_owner()
    async def shard_con(self, ctx, shard_id: int):
        try:
            self.bot.get_shard(shard_id).connect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @command()
    @is_owner()
    async def reload(self, ctx, cog: str):
        # Reloads a given Cog
        try:
            self.bot.reload_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @command()
    @is_owner()
    async def load(self, ctx, cog: str):
        # Loads a given Cog
        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @command()
    @is_owner()
    async def unload(self, ctx, cog: str):
        # Unloads a given Cog
        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @command()
    @is_owner()
    async def ev(self, ctx, *, content: str):
        """Evaluates Python code
        Gracefully stolen from Rapptz ->
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py#L72-L117"""

        # Make the environment
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'self': self,
        }
        env.update(globals())

        # Make code and output string
        content = self._cleanup_code(content)
        code = f'async def func():\n{textwrap.indent(content, "  ")}'

        # Make the function into existence
        stdout = io.StringIO()
        try:
            exec(code, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        # Grab the function we just made and run it
        func = env['func']
        try:
            # Shove stdout into StringIO
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            # Oh no it caused an error
            stdout_value = stdout.getvalue() or None
            message = utils.embed_message(message=f'```py\n{stdout_value}\n{traceback.format_exc()}\n```',
                                          footer_icon=self.bot.user.avatar_url)
            await ctx.send(embed=message)
        else:
            # Oh no it didn't cause an error
            stdout_value = stdout.getvalue() or None

            # Give reaction just to show that it ran
            await ctx.message.add_reaction("\N{OK HAND SIGN}")

            # If the function returned nothing
            if ret is None:
                # It might have printed something
                if stdout_value is not None:
                    message = utils.embed_message(message=f'```py\n{stdout_value}\n```',
                                                  footer_icon=self.bot.user.avatar_url)
                    await ctx.send(embed=message)
                return

            # If the function did return a value
            result_raw = stdout_value or ret  # What's returned from the function
            result = str(result_raw)  # The result as a string
            if result_raw is None:
                return
            text = f'```py\n{result}\n```'
            if type(result_raw) == dict:
                try:
                    result = json.dumps(result_raw, indent=4)
                except Exception:
                    pass
                else:
                    text = f'```json\n{result}\n```'
            if len(text) > 2000:
                await ctx.send(file=discord.File(io.StringIO(result), filename='ev.txt'))
            else:
                message = utils.embed_message(message=text,
                                              footer_icon=self.bot.user.avatar_url)
                await ctx.send(embed=message)


def setup(bot):
    bot.add_cog(Developer(bot))