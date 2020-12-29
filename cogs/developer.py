import ast
import collections
import contextlib
import glob
import io
import logging
import os
import json
import textwrap
import traceback
import re
import typing

from jishaku.codeblocks import codeblock_converter
from PIL import Image as PILImage, ImageDraw, ImageFont
import pytesseract

import discord
from discord.ext import menus, commands
from discord.ext.commands import (
    Cog, is_owner, BadArgument, group, Converter
)

from utils.embed import Embed

import utils
import config as cfg

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


class SQLListPageSource(menus.ListPageSource):
    def __init__(self, data, *, per_page=10):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu, page):
        embed = Embed.default(menu.ctx)
        embed.description = (f"```py\n" +
                             "\n".join(page) +
                             "```")
        embed.set_footer(
            text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return embed


class Developer(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self._last_result = None
        self.bot: utils.MyBot = bot
        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

    async def cog_check(self, ctx: utils.CustomContext):
        return await self.bot.is_owner(ctx.author)

    def _exec_then_eval(self, ctx: utils.CustomContext, code):
        """Helper method to help evaluate python code."""

        block = ast.parse(code, mode="exec")
        last = ast.Expression(block.body.pop().value)

        _globals = {
            "ctx": ctx,
            "bot": ctx.bot,
            "guild": ctx.guild,
            "channel": ctx.channel,
            "author": ctx.author,
            "message": ctx.message,
            "find": discord.utils.find,
            "get": discord.utils.get,
            "_": self._last_result,
        }
        _globals.update(globals())
        _locals = {}

        exec(compile(block, "<string>", mode="exec"), _globals, _locals)
        return eval(compile(last, "<string>", mode="eval"), _globals, _locals)

    @group(invoke_without_command=True)
    @is_owner()
    async def dev(self, ctx: utils.CustomContext):
        pass

    @dev.command(name="blacklist")
    async def dev_blacklist(self, ctx: utils.CustomContext, user: discord.Member, *, reason: str = "None"):
        """Blacklists a user from using the bot globally."""

        if user.id in self.bot.blacklist.keys():
            return await ctx.send("That user is already blacklisted.")

        await self.bot.pool.execute("INSERT INTO blacklist VALUES($1, $2)",
                                    user.id, reason)
        self.bot.blacklist[user.id] = reason

        await ctx.send(
            "\N{OK HAND SIGN} Successfully blacklisted that user."
        )

    @dev.command(name="ocr")
    async def dev_ocr(self, ctx: utils.CustomContext, url: str):
        """OCR Testing"""

        async with self.bot.session.get(url) as response:
            img_bytes = await response.read()

            def process_img(instream):
                # Get Image to OCR
                stream = io.BytesIO(instream)
                img = PILImage.open(stream).convert("1")
                img.save(stream, "png")
                stream.seek(0)

                return {
                    "text": pytesseract.image_to_string(img),
                    "file": discord.File(stream, "test.png")
                }

            data = await self.bot.loop.run_in_executor(None, process_img, img_bytes)

            embed = Embed.default(
                ctx,
                description=f"{data['text']}"
            )

            embed.set_image(url="attachment://test.png")

        await ctx.send(
            file=data["file"],
            embed=embed
        )

    @dev.command(name="stats")
    async def dev_stats(self, ctx: utils.CustomContext):
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

        code_count = '\n'.join(f'{key.upper()}: {count}' for key, count in ctr.items())
        server_count = sum(1 for g in self.bot.guilds)
        user_count = sum(g.member_count for g in self.bot.guilds)
        command_count = sum(1 for cmd in self.bot.walk_commands())
        ping = round(self.bot.latency * 1000)

        fields = [
            ["Server Count", server_count, True],
            ["User Count", user_count, True],
            ["Command Count", command_count, True],
            ["Command Usage (last restart)", self.bot.cmd_usage, True],
            ["Ping", ping, True],
            ["Uptime", str(self.bot.get_uptime()), True],
            ["Code Count", f"```\n{code_count}```", False]
        ]

        embed = Embed.default(ctx, title="Dev Stats")

        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

        await ctx.send(embed=embed)

    @dev.command(name="leave")
    async def dev_leave(self, ctx: utils.CustomContext):
        """Forces the bot to leave the current server"""

        await ctx.guild.leave()

    @dev.command(name="sql")
    async def dev_sql(self, ctx: utils.CustomContext, *, query: codeblock_converter):
        """Executes an SQL statement for the bot."""

        async with ctx.timeit:
            """Start timing how long it takes to process the query."""
            query = query.content

            strategy = ctx.db.fetch if query.lower().startswith("select") else ctx.db.execute

            results = await strategy(query.format(author=ctx.author,
                                                  guild=ctx.guild))

            data = []
            if isinstance(results, list):
                for result in results:
                    data.append(repr(result))
            else:
                data.append(repr(results))

            menu = utils.KalPages(SQLListPageSource(data))
            await menu.start(ctx)

    @dev.command(name="restart")
    async def dev_restart(self, ctx: utils.CustomContext, what: str):
        await ctx.send(f"⚠ Restarting {what.lower()} now...")
        if what.lower() == "bot":
            await self.bot.logout()
        elif what.lower() == "webserver":
            os.system("systemctl restart webserver")
        elif what.lower() == "server":
            os.system("reboot")
        else:
            pass

    @dev.command(name="say")
    async def dev_say(self, ctx: utils.CustomContext, channel: typing.Optional[discord.TextChannel] = None, *, msg: str = None):
        """You can force the bot to say stuff, cool."""

        channel = channel or ctx.channel
        await channel.send(msg)

    @dev.command(name="reload", aliases=["r"])
    async def dev_reload(self, ctx: utils.CustomContext):
        """Reloads all cogs"""

        successful = []
        unsuccessful = {}
        exts = [x for x in self.bot.extensions.keys()]
        current_cogs = [[exts[index], cog]
                        for index, cog in enumerate(self.bot.cogs.values())]
        for cog_name, cog in current_cogs:
            try:
                if cog_name == "cogs.music":
                    continue

                self.bot.reload_extension(cog_name)
                if hasattr(cog, "show_name"):
                    successful.append(f"`{cog_name[5:]}`")
            except Exception as e:
                unsuccessful[cog_name] = f"{type(e).__name__} - {e}"

        if unsuccessful:
            fmt = ["I caught some errors:"]
            for key, value in unsuccessful.items():
                error = f"{key} - {value}"
                fmt.append(error)

            await ctx.send("\n".join(fmt))

        await ctx.send(f"Successfully reloaded:\n{', '.join(successful)}", new_message=True)

    @dev.command(name="load")
    async def dev_load(self, ctx: utils.CustomContext, *cogs: str):
        """Loads given cog(s)"""

        successful = []
        unsuccessful = {}

        for cog in cogs:
            try:
                self.bot.load_extension(cog)
                successful.append(cog)
            except Exception as e:
                unsuccessful[cog] = f"{type(e).__name__} - {e}"

        await ctx.send(f"I successfully loaded {', '.join(successful)}")

        if unsuccessful:
            fmt = "\n".join([f"{key} - {value}" for key, value in unsuccessful.items()])
            await ctx.send(
                "Though there were some errors loading something:\n" +
                fmt
            )

    @dev.command(name="unload")
    async def dev_unload(self, ctx: utils.CustomContext, *cogs: str):
        """Unloads given cog(s)"""

        successful = []
        unsuccessful = {}

        for cog in cogs:
            try:
                self.bot.unload_extension(cog)
            except Exception as e:
                unsuccessful[cog] = f"{type(e).__name__} - {e}"

        await ctx.send(f"I successfully unloaded {', '.join(successful)}")

        if unsuccessful:
            fmt = "\n".join([f"{key} - {value}" for key, value in unsuccessful.items()])
            await ctx.send(
                "Though there were some errors unloading something:\n" +
                fmt
            )

    @dev.command(name="ev")
    async def dev_ev(self, ctx: utils.CustomContext, *, code: codeblock_converter):
        """Evaluates Python Code."""

        try:
            result = self._exec_then_eval(ctx, code.content)
        except Exception as e:
            await ctx.message.add_reaction("<:doubleexclamation:783295580218064947>")
            fmt_exc = f"{type(e).__name__}: {e}"
            return await ctx.send(
                f"```py\n{''.join(traceback.format_tb(e.__traceback__))}\n{fmt_exc}```"
            )

        await ctx.message.add_reaction("<:checkmark:783295580298018827>")
        self._last_result = result

        if isinstance(result, discord.Embed):
            return await ctx.send(embed=result)

        return await ctx.send(result)


def setup(bot):
    bot.add_cog(Developer(bot))
