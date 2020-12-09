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
import typing

import KalDiscordUtils
from jishaku import codeblocks
from polaroid import Image
from PIL import Image as PILImage, ImageDraw, ImageFont
import pytesseract

import discord
from discord.ext import tasks, commands, menus
from discord.ext.commands import (
    Cog, is_owner, BadArgument, group, Converter
)

from utils import utils
from utils.CustomBot import MyBot
from utils.CustomContext import CustomContext
from utils.Embed import Embed
from utils.Paginator import BetterPaginator, Menu, LPS, KalPages

from selenium import webdriver

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


class SQLCommandPages(menus.ListPageSource):
    def __init__(self, ctx, data):
        super().__init__(data, per_page=4)
        self.ctx = ctx

    async def format_page(self, menu, page):
        embed = KalDiscordUtils.Embed.default(
            self.ctx,
            title="SQL Result:",
            description=(
                "```\n" +
                "\n".join(page) +
                "```"
            )
        )
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")

        return embed


class Developer(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self._last_result = None
        self.bot: MyBot = bot
        self.check_premium.start()

    async def cog_check(self, ctx: CustomContext):
        return await self.bot.is_owner(ctx.author)

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
    async def dev(self, ctx: CustomContext):
        pass

    @dev.command(name="test")
    async def dev_test(self, ctx: CustomContext):
        """Testing PIL"""

        buffer = io.BytesIO()

        text = "The quick brown fox jumped over the lazy dog longer test lol watch this."
        wrapped_text = textwrap.wrap(text, width=30)
        text = "\n".join(wrapped_text)
        size = ImageFont.load_default().getsize(text)

        with PILImage.new("RGB", (size[0], (size[1] * (len(wrapped_text) + 1)) + 5), 0x2150c1) as base:

            canvas = ImageDraw.Draw(base)
            canvas.multiline_text((5, 5), text)

            base.save(buffer, "png")

        buffer.seek(0)

        await ctx.send(file=discord.File(buffer, "test.png"))

    @dev.command(name="ss")
    async def dev_ss(self, ctx: CustomContext, url: str):
        """Website screenshotting"""

        def ss_website(web_url) -> io.BytesIO:
            from selenium import webdriver
            path = './scrape.png'

            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("start-maximized")
            chrome_options.add_argument("disable-infobars")
            # 9100
            # chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_experimental_option(
                "UseAutomationExtension", False)
            chrome_options.headless = True

            driver = webdriver.Chrome(executable_path='/root/chromedriver',
                                      chrome_options=chrome_options)
            driver.get(web_url)
            el = driver.find_element_by_tag_name('body')
            el.screenshot(path)
            driver.quit()
            img = Image("./scrape.png")
            obj = io.BytesIO(img.save_bytes())

            return obj

        async with ctx.typing():
            obj = await self.bot.loop.run_in_executor(None, ss_website, url)
            file = discord.File(obj, filename="scrape.png")
            await ctx.send(file=file)

    @dev.command(name="ocr")
    async def dev_ocr(self, ctx: CustomContext, url: str):
        """OCR Testing"""

        async with self.bot.session.get(url) as response:
            img_bytes = await response.read()

            def process_img(instream):
                # Get Image to OCR
                stream = io.BytesIO(instream)
                img = PILImage.open(stream)

                return {"text": pytesseract.image_to_string(img)}

            data = await self.bot.loop.run_in_executor(None, process_img, img_bytes)

            embed = Embed.default(
                ctx,
                description=f"{data['text']}"
            )

            embed.set_image(url=url)

        await ctx.send(embed=embed)

    @dev.command(name="stats")
    async def dev_stats(self, ctx: CustomContext):
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
    async def dev_leave(self, ctx: CustomContext):
        """Forces the bot to leave the current server"""

        await ctx.guild.leave()

    @dev.command(name="sql")
    async def dev_sql(self, ctx: CustomContext, *, query: str):
        """Executes an SQL statement for the bot."""

        if query.lower().startswith("select"):
            stratergy = self.bot.pool.fetch
        else:
            stratergy = self.bot.pool.execute

        results = await stratergy(query)
        statements = []

        if isinstance(results, list):
            for result in results:
                statements.append(repr(result))
        elif isinstance(results, str):
            statements.append(results)

        menu = KalPages(source=SQLCommandPages(ctx, statements))
        await menu.start(ctx)

    @dev.command(name="restart")
    async def dev_restart(self, ctx: CustomContext):
        await ctx.send("⚠ Restarting now...")
        if self.bot.user.id == 706530005169209386:
            os.system("systemctl restart travis")
        else:
            os.system("systemctl restart mybot")

    @dev.command()
    async def add_premium(self, ctx: CustomContext, guild_id: int, sub_time: TimeConverter):
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
    async def dev_say(self, ctx: CustomContext, channel: typing.Optional[discord.TextChannel] = None, *, msg: str = None):
        """You can force the bot to say stuff, cool."""

        channel = channel or ctx.channel
        await channel.send(msg)

    @dev.command(name="kill")
    async def dev_kill(self, ctx: CustomContext):
        try:
            self.bot.clear()
            await self.bot.close()
        except Exception as e:
            await ctx.send(
                "Couldn't kill the bot for some reason, maybe this will help:\n"
                + f"{type(e).__name__} - {e}"
            )

    @dev.command()
    async def shard_recon(self, ctx: CustomContext, shard_id: int):
        try:
            self.bot.get_shard(shard_id).reconnect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command()
    async def shard_discon(self, ctx: CustomContext, shard_id: int):
        try:
            self.bot.get_shard(shard_id).disconnect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command()
    async def shard_con(self, ctx: CustomContext, shard_id: int):
        try:
            self.bot.get_shard(shard_id).connect()
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command(name="reload", aliases=["r"])
    async def dev_reload(self, ctx: CustomContext, cog: str = None):
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
    async def dev_load(self, ctx: CustomContext, cog: str):
        # Loads a given Cog
        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command(name="unload")
    async def dev_unload(self, ctx: CustomContext, cog: str):
        # Unloads a given Cog
        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @dev.command(name="ev")
    async def dev_ev(self, ctx: CustomContext, *, content: str):
        """Evaluates Python code
        Gracefully stolen from Rapptz ->
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py#L72-L117"""

        # Make the environment
        env = {
            "client": self.bot,
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
