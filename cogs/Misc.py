import json
import time
import typing
import re
from decouple import config
import discord
from discord.ext import commands, menus

from utils import utils
from utils.Embed import Embed
from utils.CustomCog import BaseCog
import KalDiscordUtils

from utils.Paginator import KalPages


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


class Misc(BaseCog, name="misc"):
    """Miscellaneous Commands"""

    def __init__(self, bot, show_name):
        self.bot = bot
        self.show_name = show_name

    @commands.command(name="commands", aliases=["cmds"])
    async def _commands(self, ctx, *, category: CogConverter = None):

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
    async def quote(self, ctx, message: discord.Message, *, quote: str):
        """Old Discord quoting system"""

        allowed_mentions = discord.AllowedMentions.none()
        await ctx.send(
            f"> {message.clean_content}\n"
            f"{message.author.mention} {quote} "
            f"|| Message from {ctx.author} ||",
            allowed_mentions=allowed_mentions
        )

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rawmsg(self, ctx, message: discord.Message):
        """Gets the raw JSON data of a message, if you don't know what that is, this command probably isn't for you."""

        async with self.bot.session.get(
                f"https://discord.com/api/v8/channels/{message.channel.id}/messages/{message.id}",
                headers={"Authorization": f"Bot {self.bot.http.token}"}) as r:
            if r.status != 200:
                return await ctx.send("So that just didn't work.")

            r = await r.json()

        formatted = json.dumps(r, indent=4)
        msg = f"{formatted}"

        if len(msg) > 2000:
            paginator = commands.Paginator(
                max_size=2000,
                prefix="```json",
                suffix="```"
            )
            paginator.add_line(line=msg[:1988])
            paginator.add_line(line=msg[1988:])

        if len(msg) < 2000:
            message = await ctx.send(f"```json\n{msg}```")
            await self.bot.add_delete_reaction(ctx.channel.id, message.id)
        else:
            menu = KalDiscordUtils.Menu(paginator.pages, embed=False)
            start_menu = await menu.start(ctx)

    @commands.command(aliases=["dstatus"])
    async def discordstatus(self, ctx):
        """Gets the current status of Discord."""

        async with self.bot.session.get("https://discordstatus.com/history.json") as response:
            data = await response.json()
            current = data["months"][0]["incidents"][0]
            components = data["components"]

            timestamp = re.sub(
                r"<var data-var='date'>|</var>|<var data-var='time'>", "", current["timestamp"])

            main_embed = Embed.default(
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

            comp_list = []

            for _set in components:
                comp_list.append(
                    f"Name: {_set['name']} -> **{_set['status']}**"
                )

            components_embed = Embed.default(
                ctx,
                title="Components",
                description="\n".join(comp_list)
            )

            p = KalDiscordUtils.Menu([main_embed, components_embed],
                                     clear_reactions_after=True)
            await p.start(ctx)

    @commands.command(aliases=["latency"])
    async def ping(self, ctx):
        """Get the bots ping."""

        embed = Embed.default(ctx)
        embed.add_field(
            name="Heartbeat Latency",
            value=f"{(ctx.bot.latency * 1000):,.2f} ms"
        )
        start = time.perf_counter()
        msg = await ctx.send(embed=embed)
        end = time.perf_counter()
        embed.add_field(
            name="Response Latency",
            value=f"{((end - start) * 1000):,.2f} ms"
        )
        await msg.edit(embed=embed)

    @commands.command()
    async def password(self, ctx, length: typing.Optional[int] = 8):
        """Generates a password and sends it to you in DMs!"""

        url = f"http://kal-byte.co.uk:4040/passwordgen/{length}"
        async with self.bot.session.get(url) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status.")
            data = await r.json()
            password = discord.utils.escape_markdown(data["data"])
            try:
                if len(password) > 2000:
                    return await ctx.send("That password is too long...")

                await ctx.author.send(
                    "Here is your newly generated password:\n"
                    f"{password}"
                )
                await ctx.send("Check your DMs to get your generated password.")
            except discord.Forbidden:
                await ctx.send(
                    "I could not send the password to you. "
                    "Please make sure you can receive DMs from the bot."
                )

    @commands.command(hidden=True, aliases=["hello"])
    async def hey(self, ctx):
        """Displays the bots introduction."""

        await ctx.send(
            f"Hello {ctx.author.mention} I am a bot created by kal#1806 made for general purpose, utilities and moderation."
        )

    @commands.command()
    async def privacy(self, ctx):
        """Sends the bots privacy policy via dms."""

        message = """What information is stored?
- Server ID's, Channel ID's, User ID's will be saved for the use of features such as Mutes, verification etc.

Why this information is stored and how we use it.
- This information is stored to keep the bot with the most up to date info that allows it to keep running it's correct service.
- The mute data is stored temporarily and is used to check when the mute is supposed to end, or if you're supposed to be muted if you join or leave.

Who gets this data?
- The bot developer(s).
- If you're muted then your mute data will be formed into something readable by the `Moderations` command and this can be seen by any server staff member.

How to remove your data.
- If you'd like to get your servers data out of the bot then please either use the correct commands if given an option or contact the bot developer (kal#1806) for more information."""

        await ctx.author.send(message)

    @commands.command()
    async def suggest(self, ctx, *, suggestion: str):
        """Send a suggestion to the bot developer."""

        msg = f"**Suggestion from {ctx.author} ({ctx.author.id}) at {ctx.message.created_at}**\n{suggestion}"
        await ctx.bot.get_channel(710978375426244729).send(msg)
        await ctx.thumbsup()

    @commands.command()
    async def invite(self, ctx):
        """Sends an link to invite the bot to your server."""

        bot_invite = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot"

        embed = Embed.default(
            ctx,
            title="Invite the bot to your server here!"
        )

        embed.url = bot_invite

        await ctx.send(embed=embed)

    @commands.command()
    async def support(self, ctx):
        """Gives a link to the support server."""

        await ctx.send(
            "If you need help with the bot please join the support server:\n"
            + f"{config('SUPPORT_LINK')}"
        )

    @commands.command()
    async def uptime(self, ctx):
        """Get the bots uptime."""

        await ctx.send(f"Uptime: {self.bot.get_uptime()}")

    @commands.command(aliases=["git", "code", "src"])
    async def github(self, ctx):
        """Sends the bots github repo"""

        await ctx.send(
            "Here's my source code, if you decide to use my code please star my repo :}:\n"
            f"{config('GITHUB_LINK')}"
        )


def setup(bot):
    bot.add_cog(Misc(bot, "💫 Misc"))
