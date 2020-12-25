import io
import json
import time
import typing
import re

import asynckapi
from decouple import config
import discord
from discord.ext import commands, menus
from jishaku.codeblocks import codeblock_converter
from selenium import webdriver

import utils
import KalDiscordUtils

from utils.paginator import KalPages


"""
This Jishaku stuff was gracefully stolen from Stella
"""

import contextlib
import jishaku.paginators
import jishaku.exception_handling
from collections import namedtuple
from typing import Union

EmojiSettings = namedtuple('EmojiSettings', 'start back forward end close')


class FakeEmote(discord.PartialEmoji):

    @classmethod
    def from_name(cls, name):
        emoji_name = re.sub("|<|>", "", name)
        a, name, id = emoji_name.split(":")
        return cls(name=name, id=int(id), animated=bool(a))


emote = EmojiSettings(
    start=FakeEmote.from_name("<:leftbigarrow:780746237766664192>"),
    back=FakeEmote.from_name("<:leftarrow:780746237825646672>"),
    forward=FakeEmote.from_name("<:righarrow:780746237807820800>"),
    end=FakeEmote.from_name("<:rightarrowbig:780746237829840926>"),
    close=FakeEmote.from_name("<:stop:780746237527064578>")
)
jishaku.paginators.EMOJI_DEFAULT = emote  # Overrides jishaku emojis


# noinspection PyDictDuplicateKeys
async def attempt_add_reaction(msg: discord.Message, reaction: Union[str, discord.Emoji]):
    """
    This is responsible for every add reaction happening in jishaku. Instead of replacing each emoji that it uses in
    the source code, it will try to find the corresponding emoji that is being used instead.
    """
    reacts = {
        "\N{WHITE HEAVY CHECK MARK}": "<:checkmark:783295580298018827>",
        "\N{BLACK RIGHT-POINTING TRIANGLE}": emote.forward,
        "\N{HEAVY EXCLAMATION MARK SYMBOL}": "<:exclamation:783295580545220618>",
        "\N{DOUBLE EXCLAMATION MARK}": "<:doubleexclamation:783295580218064947>",
        "\N{ALARM CLOCK}": emote.end
    }
    react = reacts[reaction] if reaction in reacts else reaction
    with contextlib.suppress(discord.HTTPException):
        return await msg.add_reaction(react)


jishaku.exception_handling.attempt_add_reaction = attempt_add_reaction


class CogConverter(commands.Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        cog = ctx.bot.get_cog(argument)
        showable = hasattr(cog, "show_name")
        if cog is None or not showable:
            raise commands.BadArgument("That category was not found.")

        return cog


class CommandCatList(menus.ListPageSource):
    def __init__(self, ctx, cog_name, data):
        super().__init__(data, per_page=4)
        self.data = data
        self.ctx = ctx
        self.cog_name = cog_name

    async def format_page(self, menu, cmds):
        embed = KalDiscordUtils.Embed.default(
            self.ctx,
            title=self.cog_name,
            description="\n".join(cmds)
        )

        return embed


class CommandsList(menus.ListPageSource):
    def __init__(self, ctx, data):
        super().__init__(data, per_page=4)
        self.data = data
        self.ctx = ctx

    async def format_page(self, menu, cmds):
        embed = KalDiscordUtils.Embed.default(
            self.ctx,
            title=cmds[0][0],
            description="\n".join([c[1] for c in cmds])
        )

        return embed


class RawMessagePaginator(menus.ListPageSource):
    def __init__(self, raw_message: list):
        super().__init__(raw_message, per_page=20)

    async def format_page(self, menu: menus.Menu, page: list):
        embed = KalDiscordUtils.Embed.default(menu.ctx)
        embed.description = "```json\n" + "\n".join(page) + "```"

        return embed

class BlockingFunctions:

    @staticmethod
    def screenshot(web_url) -> io.BytesIO:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.headless = True

        driver = webdriver.Chrome(executable_path='/root/chromedriver',
                                  chrome_options=chrome_options)

        driver.get(web_url)

        el = driver.find_element_by_tag_name('body')
        screenshot_bytes = el.screenshot_as_png

        obj = io.BytesIO(screenshot_bytes)
        driver.quit()

        return obj


class Misc(utils.BaseCog, name="misc"):
    """Miscellaneous Commands"""

    def __init__(self, bot, show_name):
        self.blacklist = [466297117409804318,
                          755096934707888219,
                          671431400423030786,
                          700745848119885845,
                          742262208167280641,
                          281111308844400660,
                          510698308248010792,
                          758861325039566868]
        self.bot: utils.MyBot = bot
        self.show_name = show_name

    @commands.Cog.listener()
    async def on_command(self, ctx: utils.CustomContext):
        self.bot.cmd_usage += 1
        if ctx.guild:
            if not ctx.guild.chunked:
                await ctx.guild.chunk(cache=True)

    @commands.command()
    async def script(self, ctx: utils.CustomContext, *, script: codeblock_converter):
        """Heavily work in progress."""

        import scripting

        script = script[1].split(
            "\n")[1:-1] if len(script[1].split("\n")) > 3 else script[1]
        script = "".join(script) if isinstance(script, list) else script

        lexer = scripting.LeLexer()
        parser = scripting.LeParser()
        env = {}

        tree = parser.parse(lexer.tokenize(script))
        process = scripting.LeExecute(tree, env)

        if process.result is None:
            return await ctx.send("Placeholder text as this command is far from complete.")

        await ctx.send(process.result)

    @commands.command()
    async def vote(self, ctx: utils.CustomContext):
        """Gives the link to vote for Travis"""

        fmt = (
            f"[Click here to vote for Travis Bott :)](https://top.gg/bot/706530005169209386)\n"
            "If you genuinely enjoy the bot make sure to leave an honest review, thank you for using Travis Bott."
        )
        embed = KalDiscordUtils.Embed.default(ctx)
        embed.description = fmt

        await ctx.send(embed=embed)

    @commands.command(aliases=["ss"])
    @commands.is_nsfw()
    @commands.is_owner()
    async def screenshot(self, ctx: utils.CustomContext, url: str):
        """Screenshots a given URL.
        *Note: this is limited to NSFW channels.*"""

        async with ctx.typing():
            obj = await self.bot.loop.run_in_executor(None, BlockingFunctions.screenshot, url)
            embed = KalDiscordUtils.Embed.default(ctx)

            file = discord.File(obj, filename="scrape.png")
            embed.set_image(url="attachment://scrape.png")

            await ctx.send(
                file=file,
                embed=embed
            )

    @commands.command(name="commands", aliases=["cmds"])
    async def _commands(self, ctx: utils.CustomContext, *, category: CogConverter = None):
        """A compiled list of all commands."""

        if category:
            cmd_list = list()
            for command in category.get_commands():
                if command.help:
                    cmd_list.append(
                        f"**{command.name}** → {command.help.format(prefix=ctx.prefix)}")

            menu = KalPages(source=CommandCatList(
                ctx, category.show_name, cmd_list))
            await menu.start(ctx)

        else:
            cmd_list = list()
            for cog in self.bot.cogs:
                cog = self.bot.get_cog(cog)
                if not hasattr(cog, "show_name"):
                    continue
                for cmd in cog.get_commands():
                    if cmd.help:
                        cmd_list.append(
                            [cog.show_name, f"**{cmd.name}** → {cmd.help.format(prefix=ctx.prefix)}"])

            menu = KalPages(source=CommandsList(ctx, cmd_list))
            await menu.start(ctx)

    @commands.command()
    async def quote(self, ctx: utils.CustomContext, message: discord.Message, *, quote: str):
        """Old Discord quoting system"""

        allowed_mentions = discord.AllowedMentions.none()
        await ctx.send(
            f"> {message.clean_content}\n"
            f"{message.author.mention} {quote} "
            f"|| Message from {ctx.author} ||",
            allowed_mentions=allowed_mentions
        )

    @commands.command(cooldown_after_parsing=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rawmsg(self, ctx: utils.CustomContext, message: discord.Message):
        """Gets the raw JSON data of a message, if you don't know what that is, this command probably isn't for you."""

        async with self.bot.session.get(
                f"https://discord.com/api/v8/channels/{message.channel.id}/messages/{message.id}",
                headers={"Authorization": f"Bot {self.bot.http.token}"}) as r:
            if r.status != 200:
                return await ctx.send(
                    "Something went wrong... I can't really tell you why because I don't know BUT\n"
                    f"What I do know is that the status code is {r.status} so maybe that'd help."
                )

            r = await r.json()

        formatted = json.dumps(r, indent=4)
        lines = [line for line in formatted.splitlines()]

        source = RawMessagePaginator(lines)
        menu = utils.KalPages(source)
        await menu.start(ctx)

    @commands.command(aliases=["dstatus"])
    async def discordstatus(self, ctx: utils.CustomContext):
        """Gets the current status of Discord."""

        async with self.bot.session.get("https://discordstatus.com/history.json") as response:
            data = await response.json()
            try:
                current = data["months"][0]["incidents"][0]
            except IndexError:
                embed = KalDiscordUtils.Embed.warning(
                    description="There are no incidents reported this month as of yet.")
                return await ctx.send(embed=embed)
            components = data["components"]

            timestamp = re.sub(
                r"<var data-var='date'>|</var>|<var data-var='time'>", "", current["timestamp"])

            embeds = []

            if len(timestamp) < 17:
                main_embed = KalDiscordUtils.Embed.default(
                    ctx,
                    title="Current Status for Discord.",
                    description=(
                        "```\n" +
                        f"Code: {current['code']}\n" +
                        f"Name: {current['name']}\n" +
                        f"Message: {current['message']}\n" +
                        f"Impact: {current['impact']}\n" +
                        f"Timestamp: {timestamp}\n" +
                        "```"
                    )
                )

                main_embed.url = "https://discordstatus.com/"
                embeds.append(main_embed)

            # Thank you to Cyrus#8315 for this.
            def format_comp(mapping):
                msg = "```py\n"
                longest = None

                for key in mapping:
                    length = len(key["name"])

                    if longest is None or length > longest:
                        longest = length

                for key in mapping:
                    msg += key["name"].rjust(longest, " ") + \
                        " → " + key["status"].title() + "\n"

                msg += "```"
                return msg

            components_embed = KalDiscordUtils.Embed.default(
                ctx,
                title="Components",
                description=format_comp(components)
            )
            embeds.append(components_embed)

            source = utils.EmbedMenu(embeds)
            menu = utils.KalPages(source)
            await menu.start(ctx)

    @commands.command(aliases=["latency"])
    async def ping(self, ctx: utils.CustomContext):
        """Get the bots ping."""

        response_start = time.perf_counter()
        message = await ctx.send("Pinging...")
        response_end = time.perf_counter()
        response_fmt = f"{(response_end - response_start) * 1000:,.2f}"

        db_start = time.perf_counter()
        call = await ctx.db.fetch("SELECT 1;")
        db_end = time.perf_counter()
        db_fmt = f"{(db_end - db_start) * 1000:,.2f}"

        hb_fmt = f"{self.bot.latency * 1000:,.2f}"

        pings = [
            ["Heartbeat Latency", f"{hb_fmt} ms"],
            ["Response Latency", f"{response_fmt} ms"],
            ["Database Latency", f"{db_fmt} ms"]
        ]

        embed = KalDiscordUtils.Embed.default(ctx)
        [embed.add_field(name=k, value=v) for k, v in pings]

        await message.edit(content=None,
                           embed=embed)

    @commands.command()
    async def password(self, ctx: utils.CustomContext, length: typing.Optional[int] = 8):
        """Generates a password and sends it to you in DMs!"""

        client = asynckapi.Client()
        password = await client.password(length=length)
        password = discord.utils.escape_markdown(password)

        try:
            fmt = (
                "Here's your freshly baked password:\n"
                f"{password}"
            )
            await ctx.author.send(fmt)
            await ctx.send("Check your DMs to receive your freshly generated password.")

        except (discord.HTTPException, discord.Forbidden):
            await ctx.send("I couldn't DM you your password, sorry.")

        finally:
            await client.close()

    @commands.command(hidden=True, aliases=["hello"])
    async def hey(self, ctx: utils.CustomContext):
        """Displays the bots introduction."""

        await ctx.send(
            f"Hello {ctx.author.mention} I am a bot created by kal#1806 made for general purpose, utilities and moderation."
        )

    @commands.command(cooldown_after_parsing=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def suggest(self, ctx: utils.CustomContext, *, suggestion: str):
        """Send a suggestion to the bot developer."""

        if ctx.author.id in self.blacklist:
            return await ctx.send("It was fine for a while but I'm not allowing this, if you have a genuine suggestion feel free to contact kal#1806 :)")
        msg = f"**Suggestion from {ctx.author} ({ctx.author.id}) at {ctx.message.created_at}**\n{suggestion}"
        await ctx.bot.get_channel(710978375426244729).send(msg)
        await ctx.thumbsup()

    @commands.command()
    async def invite(self, ctx: utils.CustomContext):
        """Sends an link to invite the bot to your server."""

        embed = KalDiscordUtils.Embed.default(
            ctx,
            title="Invite the bot to your server here!"
        )

        embed.url = self.bot.invite_url

        await ctx.send(embed=embed)

    @commands.command()
    async def support(self, ctx: utils.CustomContext):
        """Gives a link to the support server."""

        await ctx.send(
            "If you need help with the bot please join the support server:\n"
            f"{self.bot.support_url}"
        )

    @commands.command()
    async def uptime(self, ctx: utils.CustomContext):
        """Get the bots uptime."""

        await ctx.send(f"Uptime: {self.bot.get_uptime()}")

    @commands.command(aliases=["git", "code", "src", "source"])
    async def github(self, ctx: utils.CustomContext):
        """Sends the bots github repo"""

        await ctx.send(
            "Here's my source code, if you decide to use my code please star my repo :}:\n"
            f"<{self.bot.github_url}>"
        )


def setup(bot):
    bot.add_cog(Misc(bot, "💫 Misc"))
