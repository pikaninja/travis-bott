import asyncio
import contextlib
import io
import json
import textwrap
import traceback
import re
import time

from discord import colour
from utils.utils import check_role_permissions

import discord
from discord.ext import tasks
from discord.ext.commands import (
    Cog, command, is_owner, Converter,
    BadArgument
)
from discord.ext.commands.core import check

from utils import utils, db
from utils.Paginator import Paginator

time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(Converter):
    async def convert(self, ctx, argument):
        args = argument.lower()
        matches = re.findall(time_regex, args)
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise BadArgument("{} is not a number!".format(v))
        return time

# noinspection PyBroadException
class Developer(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self._last_result = None
        self.bot = bot
        self.check_premium.start()

    @tasks.loop(seconds=300.0)
    async def check_premium(self):
        await self.bot.wait_until_ready()
        now = int(time.time())
        for guild_id, end_time in self.bot.premium_guilds:
            if end_time - now <= 0:
                await self.bot.pool.execute("DELETE FROM premium WHERE guild_id = $1", guild_id)
                utils.log(f"Successfully removed {guild_id} from the premium table.")
            else:
                continue

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
    async def testing(self, ctx):
        embeds = [discord.Embed(colour=0xff0000), discord.Embed(colour=0x00ff00), discord.Embed(colour=0x0000ff)]
        p = Paginator(embeds, ["\N{SLEUTH OR SPY}"], False, 10.0, True)
        await p.paginate(ctx)

    @command()
    @is_owner()
    async def add_premium(self, ctx, guild_id: int, sub_time: TimeConverter):
        """Adds premium to a guild for a given amount of time."""

        prem_time = int((time.time() + sub_time))

        async with self.bot.pool.acquire() as con:
            await con.execute("INSERT INTO premium(guild_id, end_time) VALUES($1, $2)",
                guild_id, prem_time
            )
        
        self.bot.premium_guilds[guild_id] = prem_time
        await ctx.send(f"Successfully added premium to {guild_id} for {sub_time} seconds.")

    @command()
    @is_owner()
    async def say(self, ctx, channel: discord.TextChannel, *, msg: str = None):
        """You can force the bot to say stuff, cool."""

        channel = channel or ctx.channel
        await channel.send(msg)

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
    async def reload(self, ctx, cog: str = None):
        # Reloads a given Cog

        if cog is None:
            for ext in self.bot.exts:
                try:
                    self.bot.reload_extension(ext)
                except Exception as e:
                    await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
            embed = utils.embed_message(message=f"Successfully reloaded:\n{', '.join([f'`{ext[5:]}`' for ext in self.bot.exts])}")
            await ctx.send(embed=embed)
        else:
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