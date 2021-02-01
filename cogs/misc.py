"""
Miscellaneous commands for users to use. 
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

import io
import json
import logging
import time
import re
import utils
import discord
import ksoftapi
from discord.ext import commands, menus
from json.decoder import JSONDecodeError
from discord.errors import HTTPException
from jishaku.codeblocks import codeblock_converter
from selenium import webdriver
from utils.paginator import KalPages


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
        embed = menu.ctx.bot.embed(
            menu.ctx,
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
        embed = menu.ctx.bot.embed(
            menu.ctx,
            title=cmds[0][0],
            description="\n".join([c[1] for c in cmds])
        )

        return embed


class RawMessagePaginator(menus.ListPageSource):
    def __init__(self, raw_message: list):
        super().__init__(raw_message, per_page=16)

    async def format_page(self, menu: menus.Menu, page: list):
        embed = menu.ctx.bot.embed(menu.ctx)
        embed.description = "```json\n" + \
            "\n".join(page).replace("`", "`\N{ZERO WIDTH SPACE}") + "```"

        return embed


class LyricsPaginator(menus.ListPageSource):
    def __init__(self, lyrics: list):
        super().__init__(lyrics, per_page=20)

    async def format_page(self, menu: menus.Menu, page: list):
        with menu.ctx.embed() as e:
            e.set_author(
                name=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
            e.set_footer(text="Lyrics provided by KSoft.Si.")
            e.description = "\n".join(page)
            return e


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


class Misc(commands.Cog, name="misc"):
    """Miscellaneous Commands"""

    def __init__(self, bot):
        self.blacklist = [466297117409804318,
                          755096934707888219,
                          671431400423030786,
                          700745848119885845,
                          742262208167280641,
                          281111308844400660,
                          510698308248010792]
        self.bot: utils.MyBot = bot
        self.show_name = "\N{DIZZY SYMBOL} Misc"
        self.supporters = {}

        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

    @commands.Cog.listener()
    async def on_command(self, ctx: utils.CustomContext):
        self.bot.cmd_usage += 1
        # if ctx.guild:
        #     if not ctx.guild.chunked:
        #         await ctx.guild.chunk()

    @commands.command()
    async def status(self, ctx: utils.CustomContext):
        """Gets the status of how Travis is doing right now."""

        with ctx.embed() as e:
            summary = []
            latency = round(self.bot.latency * 1000, 2)
            summary.append(f"Latency: {latency} ms.")

            async with self.bot.session.get("https://www.travisbott.rocks/") as r:
                if r.status != 200:
                    summary.append(f"Website is returning a {r.status} status.")
                else:
                    summary.append(f"Website is fully operational.")

            summary.append("Well the bot is online since you can see this message \N{THINKING FACE}.")

            e.description = "\n".join(summary)
            await ctx.send(embed=e)

    @commands.command()
    async def lyrics(self, ctx: utils.CustomContext, *, song_name: str):
        """Get the lyrics to any given song, if the song is found."""

        ksoft = ksoftapi.Client(self.bot.settings["keys"]["ksoft_api"])
        try:
            results = await ksoft.music.lyrics(song_name)
        except ksoftapi.NoResults:
            return await ctx.send(f"No lyrics found for {song_name}.")

        await ksoft.close()

        first = results[0]
        lyrics = first.lyrics.splitlines()

        source = LyricsPaginator(lyrics)
        menu = utils.KalPages(source)
        await menu.start(ctx)

    @commands.command()
    async def embedbuilder(self, ctx: utils.CustomContext, *, embed_code: codeblock_converter):
        """Builds a given embed.
        You can build the embed using this site:
        https://embedbuilder.nadekobot.me/"""

        try:
            embed_json = json.loads(embed_code.content)
        except JSONDecodeError:
            raise commands.BadArgument(
                "That was not valid Embed code. Use <https://embedbuilder.nadekobot.me/>")

        embed = discord.Embed.from_dict(embed_json)

        try:
            await ctx.send(embed=embed)
        except HTTPException:
            raise commands.BadArgument(
                "That was not valid Embed code. Use <https://embedbuilder.nadekobot.me/>")

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
    async def supporters(self, ctx: utils.CustomContext):
        """Gives a list of all the people who helped support and grow Travis Bott."""

        if not self.supporters:
            pikaninja = await self.bot.fetch_user(678401615333556277)
            astro = await self.bot.fetch_user(285506580919877633)
            cyrus = await self.bot.fetch_user(668906205799907348)

            self.supporters = {
                str(pikaninja): "Helping with growth on Travis Bott.",
                str(astro): "Helping design all of the graphics for Travis Bott.",
                str(cyrus): "Helping by contributing to the repository.",
                "Everyone who gives valid suggestions": "A lot of the commands wouldn't have been made without you."
            }

        supporters = (
            "Thank you to these people who've helped supported Travis Bott:\n",
            "\n".join(f"{k} - {v}" for k, v in self.supporters.items())
        )

        await ctx.send("\n".join(supporters))

    @commands.command()
    async def vote(self, ctx: utils.CustomContext):
        """Gives the link to vote for Travis"""

        fmt = (
            f"[Click here to vote for Travis Bott on top.gg](https://top.gg/bot/706530005169209386)\n"
            f"[Click here to vote for Travis Bott on discord.boats](https://discord.boats/bot/706530005169209386)\n"
            "If you genuinely enjoy the bot make sure to leave an honest review, thank you for using Travis Bott on top.gg."
        )

        with ctx.embed() as embed:
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
            embed = self.bot.embed(ctx)

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
                embed = Embed.warning(
                    description="There are no incidents reported this month as of yet.")
                return await ctx.send(embed=embed)
            components = data["components"]

            timestamp = re.sub(
                r"<var data-var='date'>|</var>|<var data-var='time'>", "", current["timestamp"])

            embeds = []

            if len(timestamp) < 17:
                main_embed = self.bot.embed(
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

            components_embed = self.bot.embed(
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

        typing_start = time.perf_counter()
        await ctx.trigger_typing()
        typing_time_ms = ("Typing Latency",
                          (time.perf_counter() - typing_start) * 1000)

        db_start = time.perf_counter()
        await ctx.db.fetch("SELECT 1;")
        db_time_ms = ("DB Latency", (time.perf_counter() - db_start) * 1000)

        heartbeat_ms = ("Heartbeat Latency", self.bot.latency * 1000)

        with ctx.embed() as e:
            for typeof, result in typing_time_ms, db_time_ms, heartbeat_ms:
                e.add_field(
                    name=typeof,
                    value=f"{result:,.2f} ms",
                    inline=False
                )

            await ctx.send(embed=e)

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

        embed = self.bot.embed(
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

        uptime = utils.format_time(self.bot.start_time)
        await ctx.send(f"I've been up for {uptime['precise']}")

    @commands.command(aliases=["git", "code", "src", "source"])
    async def github(self, ctx: utils.CustomContext):
        """Sends the bots github repo"""

        embed = self.bot.embed(ctx)
        embed.description = (
            "Travis Bott has been set to be closed-source as of 07/01/2021. "
            "If you'd still like to view the source please contact kal#1806 "
            "with a valid reason as to why."
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def privacy(self, ctx: utils.CustomContext):
        """Sends the bots privacy policy statement."""

        fmt = (
            "Travis Bott doesn't store much data, but here is what it *does* store and why:\n"
            "User ID's get stored for numerous things such as cookie clicker leaderboards, "
            "When someone gets muted in a server etc. Guild ID's get stored also for things "
            "such as configuration purposes e.g. prefixes and mute role ids. Message ID's get "
            "stored so we're able to corrolate them to roles for our verification command.\n"
            "If you have any questions or would like any of your data removed, contact kal#1806 "
            "via discord, either add them or via the support server."
        )

        with ctx.embed() as e:
            e.description = fmt
            await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(Misc(bot))
