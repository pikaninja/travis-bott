import collections
import contextlib
import glob
import io
import os
import json
import textwrap
import traceback
import re
import time
import logging

import discord
from discord.ext import tasks
from discord.ext.commands import (
    Cog, is_owner, BadArgument, group, Converter
)

from utils import utils
from utils.Embed import Embed
from utils.Paginator import BetterPaginator

time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}


class TimeConverter(Converter):
    async def convert(self, ctx, argument):
        args = argument.lower()
        matches = re.findall(time_regex, args)
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k] * float(v)
            except KeyError:
                raise BadArgument(
                    "{} is an invalid time-key! h/m/s/d are valid!".format(k)
                )
            except ValueError:
                raise BadArgument("{} is not a number!".format(v))
        return time


class CommandConverter(Converter):
    async def convert(self, ctx, argument):
        return ctx.bot.get_command(argument)


class Developer(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self._last_result = None
        self.bot = bot
        self.check_premium.start()

    @tasks.loop(seconds=300.0)
    async def check_premium(self):
        await self.bot.wait_until_ready()
        now = int(time.time())
        to_remove = []
        for guild_id, end_time in self.bot.cache["premium_guilds"].items():
            if end_time - now <= 0:
                await self.bot.pool.execute(
                    "DELETE FROM premium WHERE guild_id = $1", guild_id
                )
                to_remove.append(guild_id)
                logging.info(
                    f"Successfully removed {guild_id} from the premium table.")
            else:
                continue
        if len(to_remove) >= 1:
            for guild_id in to_remove:
                del self.bot.cache["premium_guilds"][guild_id]
        to_remove.clear()

    @staticmethod
    def _cleanup_code(content):
        """Automatically removes code blocks from the code."""

        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            if content[-4] == "\n":
                return "\n".join(content.split("\n")[1:-1])
            return "\n".join(content.split("\n")[1:]).rstrip("`")

        # remove `foo`
        return content.strip("` \n")

    @group(invoke_without_command=True)
    @is_owner()
    async def dev(self, ctx):
        await ctx.send_help(ctx.command)

    @dev.command(name="test")
    @is_owner()
    async def dev_test(self, ctx):
        """Testing cmd"""

        embeds = [
            Embed.default(ctx, title="Test 1"),
            Embed.default(ctx, title="Test 2"),
            Embed.default(ctx, title="Test 3")
        ]

        p = BetterPaginator(ctx, entries=embeds)
        await p.paginate()

    @dev.command(name="stats")
    @is_owner()
    async def dev_stats(self, ctx):
        """Gives some stats on the bot."""

        ctr = collections.Counter()
        for ctr['file'], f in enumerate(glob.glob('./**/*.py', recursive=True)):
            with open(f) as fp:
                for ctr['line'], line in enumerate(fp, ctr['line']):
                    line = line.strip()
                    ctr['class'] += line.startswith('class')
                    ctr['function'] += line.startswith('def')
                    ctr['coroutine'] += line.startswith('async def')
                    ctr['comment'] += '#' in line
        
        code_count = '\n'.join(f'{key}: {count}' for key, count in ctr.items())
        server_count = sum(1 for g in self.bot.guilds)
        command_count = sum(1 for cmd in self.bot.commands)
        ping = round(self.bot.latency * 1000)

        fields = [
            ["Server Count", server_count, True],
            ["Command Count", command_count, True],
            ["Ping", ping, True],
            ["Uptime", str(self.bot.get_uptime()), True],
            ["Code Count", f"```\n{code_count}```", False]
        ]

        embed = Embed.default(ctx, title="Dev Stats")

        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

        await ctx.send(embed=embed)

    @dev.command(name="leave")
    @is_owner()
    async def dev_leave(self, ctx):
        """Forces the bot to leave the current server"""

        await ctx.guild.leave()

    @dev.command(name="disable")
    @is_owner()
    async def dev_disable(self, ctx, cmd: CommandConverter, *, reason):
        """Disables a command globaly for a given reason."""

        if cmd is None:
            return await ctx.send("Invalid command entered.")
        self.bot.disabled_commands[cmd] = reason
        await ctx.send(f"Successfully disabled {cmd.qualified_name} "
                       f"for the reason: {reason}")

    @dev.command(name="enable")
    @is_owner()
    async def dev_enable(self, ctx, cmd: CommandConverter):
        """Enables a command again."""

        if cmd is None:
            return await ctx.send("Invalid command entered.")
        del self.bot.disabled_commands[cmd]
        await ctx.send(f"Successfully enabled {cmd.qualified_name}")

    @dev.command(name="disabled")
    @is_owner()
    async def dev_disabled(self, ctx):
        """Gives a list of all current disabled commands."""

        await ctx.send(
            "Current disabled commands:\n" +
            "\n".join(
                [f"• {k.qualified_name} - `{v}`" for k, v
                    in self.bot.disabled_commands.items()]
            )
        )

    @dev.command(name="sql")
    @is_owner()
    async def dev_sql(self, ctx, *, query):
        """Executes an SQL statement for the bot."""

        result = await self.bot.pool.execute(query)
        await ctx.send(f"Result of query: {result}")

    @dev.command(name="restart")
    @is_owner()
    async def dev_restart(self, ctx):
        await ctx.send("⚠ Restarting now...")
        os.system("systemctl restart travis")

    @dev.command()
    @is_owner()
    async def add_premium(self, ctx, guild_id: int, sub_time: TimeConverter):
        """Adds premium to a guild for a given amount of time."""

        prem_time = int((time.time() + sub_time))

        async with self.bot.pool.acquire() as con:
            await con.execute(
                "INSERT INTO premium(guild_id, end_time) VALUES($1, $2)",
                guild_id,
                prem_time,
            )

        self.bot.cache["premium_guilds"][guild_id] = prem_time
        await ctx.send(
            f"Successfully added premium to {guild_id} for {sub_time} seconds."
        )

    @dev.command(name="say")
    @is_owner()
    async def dev_say(self, ctx, channel: discord.TextChannel = None, *, msg: str = None):
        """You can force the bot to say stuff, cool."""

        channel = channel or ctx.channel
        await channel.send(msg)

    @dev.command(name="kill")
    @is_owner()
    async def dev_kill(self, ctx):
        try:
            self.bot.clear()
            await self.bot.close()
        except Exception as e:
            await ctx.send(
                "Couldn't kill the bot for some reason, maybe this will help:\n"
                + f"{type(e).__name__} - {e}"
            )

    @dev.command()
    @is_owner()
    async def shard_recon(self, ctx, shard_id: int):
        try:
            self.bot.get_shard(shard_id).reconnect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command()
    @is_owner()
    async def shard_discon(self, ctx, shard_id: int):
        try:
            self.bot.get_shard(shard_id).disconnect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command()
    @is_owner()
    async def shard_con(self, ctx, shard_id: int):
        try:
            self.bot.get_shard(shard_id).connect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command(name="reload")
    @is_owner()
    async def dev_reload(self, ctx, cog: str = None):
        # Reloads a given Cog

        if cog is None:
            for ext in self.bot.exts:
                try:
                    self.bot.reload_extension(ext)
                except Exception as e:
                    await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
            embed = Embed.default(
                ctx,
                description=f"Successfully reloaded:\n{', '.join([f'`{ext[5:]}`' for ext in self.bot.exts])}"
            )
            await ctx.send(embed=embed)
        else:
            try:
                self.bot.reload_extension(cog)
            except Exception as e:
                await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
            else:
                await ctx.send("**`SUCCESS`**")

    @dev.command(name="load")
    @is_owner()
    async def dev_load(self, ctx, cog: str):
        # Loads a given Cog
        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command(name="unload")
    @is_owner()
    async def dev_unload(self, ctx, cog: str):
        # Unloads a given Cog
        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command(name="ev")
    @is_owner()
    async def dev_ev(self, ctx, *, content: str):
        """Evaluates Python code
        Gracefully stolen from Rapptz ->
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py#L72-L117"""

        # Make the environment
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "self": self,
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
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        # Grab the function we just made and run it
        func = env["func"]
        try:
            # Shove stdout into StringIO
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            # Oh no it caused an error
            stdout_value = stdout.getvalue() or None
            message = Embed.default(
                ctx,
                description=f"```py\n{stdout_value}\n{traceback.format_exc()}\n```"
            )
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
                    message = Embed.default(
                        ctx,
                        description=f"```py\n{stdout_value}\n```",
                    )
                    await ctx.send(embed=message)
                return

            # If the function did return a value
            result_raw = stdout_value or ret  # What's returned from the function
            result = str(result_raw)  # The result as a string
            if result_raw is None:
                return
            text = f"```py\n{result}\n```"
            if type(result_raw) == dict:
                try:
                    result = json.dumps(result_raw, indent=4)
                except Exception:
                    pass
                else:
                    text = f"```json\n{result}\n```"
            if len(text) > 2000:
                await ctx.send(
                    file=discord.File(io.StringIO(result), filename="ev.txt")
                )
            else:
                message = Embed.default(
                    ctx,
                    description=text
                )
                await ctx.send(embed=message)


def setup(bot):
    bot.add_cog(Developer(bot))
