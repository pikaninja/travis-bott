"""
Developer commands to provide the developer some useful functionalities in the program.
Copyright (C) 2021 kal-byte

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

import ast
import collections
import glob
import io
import logging
import inspect
import os
import traceback
import re
import typing
import copy
from utils.customcontext import CustomContext

from jishaku.codeblocks import codeblock_converter
from PIL import Image as PILImage
import pytesseract

import discord
from discord.ext import menus
from discord.ext.commands import (
    Cog, is_owner, BadArgument, group, Converter
)

from utils.embed import Embed

import utils

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
        embed = self.bot.embed(menu.ctx)
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

        @bot.ipc.route()
        async def get_stats(data):
            return [
                f"{len(bot.guilds):,}",
                f"{sum(g.member_count for g in bot.guilds):,}",
                f"{sum(1 for c in bot.walk_commands()):,}"
            ]

        @bot.ipc.route()
        async def get_bot_id(data):
            user = await bot.fetch_user(data.bot_id)
            if not user.bot:
                return "706530005169209386"
            return user.id

        @bot.ipc.route()
        async def get_bot_commands(data):
            cmd_list = list()

            for command in self.bot.commands:
                if not command.help or not command.cog or not hasattr(command.cog, "show_name"):
                    continue

                sig = f"tb!{command.qualified_name} {command.signature}"
                ret = {
                    "command": sig,
                    "help": command.short_doc,
                }
                cmd_list.append(ret)

            return cmd_list

    async def cog_check(self, ctx: utils.CustomContext):
        return await self.bot.is_owner(ctx.author)

    @group(invoke_without_command=True)
    @is_owner()
    async def dev(self, ctx: utils.CustomContext):
        pass

    @dev.command(name="unavailable")
    async def dev_unavailable(self, ctx: utils.CustomContext):
        """Provides a list of all unavailable guilds on the bot."""

        await ctx.send(**{"embed": self.bot.embed(title="List of all current unavailable guilds", description="\n".join(str(x.id) for x in self.bot.guilds if x.unavailable))})

    @dev.command(name="chunked")
    async def dev_chunked(self, ctx: utils.CustomContext):
        """Gives a list of all currently chunked guilds."""

        await ctx.send(**{"embed": self.bot.embed(ctx, description=f"There are currently {sum(g.chunked for g in self.bot.guilds)} guilds chunked.")})

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

            embed = self.bot.embed(
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
            if f.startswith("./env"):
                ctr['file'] -= 1
                continue

            with open(f) as fp:
                for ctr['line'], line in enumerate(fp, ctr['line']):
                    line = line.strip()
                    ctr['class'] += line.startswith('class')
                    ctr['function'] += line.startswith('def')
                    ctr['coroutine'] += line.startswith('async def')
                    ctr['comment'] += '#' in line

        code_count = '\n'.join(
            f'{key.upper()}: {count}' for key, count in ctr.items())
        server_count = sum(1 for g in self.bot.guilds)
        user_count = sum(g.member_count for g in self.bot.guilds)
        command_count = sum(1 for cmd in self.bot.walk_commands())
        ping = round(self.bot.latency * 1000)
        uptime = utils.format_time(self.bot.start_time)

        fields = [
            ["Server Count", server_count, True],
            ["User Count", user_count, True],
            ["Command Count", command_count, True],
            ["Command Usage (last restart)", self.bot.cmd_usage, True],
            ["Ping", ping, True],
            ["Uptime", uptime["precise"], True],
            ["Code Count", f"```\n{code_count}```", False]
        ]

        with ctx.embed() as embed:
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
            await self.bot.close()
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

    @dev.command(name="as")
    async def dev_as(self, ctx: utils.CustomContext, user: discord.Member, *, cmd: str):
        """Runs a command as another user."""

        alt_message = copy.copy(ctx.message)
        alt_message.author = user
        alt_message.content = ctx.prefix + cmd

        alt_context = await self.bot.get_context(alt_message, cls=type(ctx))
        await self.bot.invoke(alt_context)

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
            fmt = "\n".join([f"{key} - {value}" for key,
                             value in unsuccessful.items()])
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
            fmt = "\n".join([f"{key} - {value}" for key,
                             value in unsuccessful.items()])
            await ctx.send(
                "Though there were some errors unloading something:\n" +
                fmt
            )

    @dev.command(name="ev")
    async def dev_ev(self, ctx: utils.CustomContext, *, code: codeblock_converter):
        """Evaluates Python Code."""

        try:
            block = ast.parse(code.content, mode="exec")
            last = ast.Expression(block.body.pop().value)

            _globals = {
                "ctx": ctx,
                "bot": ctx.bot,
                "guild": ctx.guild,
                "author": ctx.author,
                "message": ctx.message,
                "channel": ctx.channel,
                "get": discord.utils.get,
                "find": discord.utils.find,
                "_": self._last_result,
            }

            _globals.update(globals())
            _locals = {}

            _eval = eval(compile(last, "<string>", mode="eval"),
                         _globals, _locals)
            exec(compile(block, "<string>", mode="exec"), _globals, _locals)

            if inspect.isawaitable(_eval):
                result = await _eval
            else:
                result = _eval
        except Exception as e:
            await ctx.message.add_reaction("\N{THUMBS DOWN SIGN}")
            fmt_exc = f"{type(e).__name__}: {e}"
            content = utils.codeblock(
                f"\n{''.join(traceback.format_tb(e.__traceback__))}\n{fmt_exc}"
            )
            return await ctx.send(content)

        await ctx.message.add_reaction("\N{OK HAND SIGN}")
        self._last_result = result

        if isinstance(result, discord.Embed):
            return await ctx.send(embed=result)

        if not isinstance(result, (str, discord.Message)):
            content = utils.codeblock(repr(result))
            return await ctx.send(content)

        content = utils.codeblock(result)
        return await ctx.send(content, new_message=True)


def setup(bot):
    bot.add_cog(Developer(bot))
