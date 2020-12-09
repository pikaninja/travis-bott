import contextlib
import datetime
import time

from discord.ext import commands, menus

from utils.CustomCog import BaseCog
from utils.Embed import Embed

import asyncio
import discord
import typing
import random
import vacefron

standard_cooldown = 3.0


class CookiesLBPage(menus.ListPageSource):
    def __init__(self, ctx, data):
        super().__init__(data, per_page=10)
        self.ctx = ctx

    async def format_page(self, menu, entries):
        embed = Embed.default(
            self.ctx,
            title="Cookie Leaderboard",
            description="\n".join(entries)
        )
        return embed


class Fun(BaseCog, name="fun"):
    """Fun Commands"""

    def __init__(self, bot, show_name):
        self.bot = bot
        self.show_name = show_name
        self._8ballResponse = [
            "It is certain",
            "It is decidedly so",
            "Without a doubt",
            "Yes, definitely",
            "You may rely on it",
            "As I see it, yes",
            "Most likely",
            "Outlook good",
            "Signs point to yes",
            "Yes",
            "Reply hazy, try again",
            "Ask again later",
            "Better not tell you now",
            "Cannot predict now",
            "Concentrate and ask again",
            "Don't bet on it",
            "My reply is no",
            "My sources say no",
            "Outlook not so good",
            "Very doubtful",
        ]

        self.all_colours = [
            "darkgreen",
            "purple",
            "orange",
            "yellow",
            "random",
            "black",
            "brown",
            "white",
            "blue",
            "cyan",
            "lime",
            "pink",
            "red",
        ]

        self.tetris_games = {}

    async def handle_cookies(self, user: discord.Member):
        """Handles added cookies to user"""

        check_if_exists = await self.bot.pool.fetchrow("SELECT * FROM cookies WHERE user_id = $1", user.id)

        if not check_if_exists:
            await self.bot.pool.execute(
                "INSERT INTO cookies(user_id, cookies) VALUES($1, $2)",
                user.id, 1
            )
        else:
            await self.bot.pool.execute(
                "UPDATE cookies SET cookies = cookies + 1 WHERE user_id = $1",
                user.id
            )

    # @commands.command()
    # @commands.is_owner()
    # async def tetris(self, ctx):
    #     """A game of tetris"""
    #
    #     width, height = (12, 22)
    #
    #     red, black, blue, green, purple, yellow, orange = (
    #         "\N{LARGE RED SQUARE}",
    #         "\N{BLACK LARGE SQUARE}",
    #         "\N{LARGE BLUE SQUARE}",
    #         "\N{LARGE GREEN SQUARE}",
    #         "\N{LARGE PURPLE SQUARE}",
    #         "\N{LARGE YELLOW SQUARE}",
    #         "\N{LARGE ORANGE SQUARE}"
    #     )

    @commands.command()
    async def chimprate(self, ctx, user: discord.Member = None):
        """Rate's someones chimpness :monkey:"""

        user = user or ctx.author
        random.seed(user.id)
        chimp_amount = random.randint(0, 100)
        await ctx.send(f"{user.name}'s chimping levels is {chimp_amount}% \N{MONKEY}")

    @commands.command(aliases=["r"])
    async def reddit(self, ctx, subreddit: str):
        """Browse your favourite sub-reddit, gives a random submission from it."""

        async with ctx.typing():
            url = f"https://www.reddit.com/r/{subreddit}/random.json"
            async with self.bot.session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.send("That subreddit doesn't exist or something severely wrong just happened.")
                data = await resp.json()
                try:
                    data = data[0]["data"]["children"][0]["data"]
                except KeyError:
                    return await ctx.send("That subreddit doesn't exist or something severely wrong just happened.")

                title, author, ups, downs, score, over_18, url, perma_link, subs, created_at = (
                    data["title"],
                    data["author"],
                    data["ups"],
                    data["downs"],
                    data["score"],
                    data["over_18"],
                    data["url"],
                    data["permalink"],
                    data["subreddit_subscribers"],
                    data["created_utc"]
                )

                if over_18:
                    if not ctx.channel.is_nsfw():
                        return await ctx.send("Bonk! Go to horny jail.")

                embed = Embed.default(ctx,
                                      title=title,
                                      url=f"https://www.reddit.com{perma_link}")

                embed.add_field(name="\N{UPWARDS BLACK ARROW}",
                                value=ups)
                embed.add_field(name="\N{DOWNWARDS BLACK ARROW}",
                                value=downs)

                embed.set_image(url=url)
                embed.set_author(name=f"Poster: {author}")
                embed.set_footer(text=f"Subreddit Subs: {subs} | Post score: {score} | Posted at")
                embed.timestamp = datetime.datetime.fromtimestamp(created_at)

                await ctx.send(embed=embed)

    @commands.group(aliases=["cc"], invoke_without_command=True)
    @commands.cooldown(1, 60, commands.BucketType.member)
    async def cookieclick(self, ctx):
        """First person to click on the cookie wins!"""

        timer = 3
        embed = Embed.default(
            ctx,
            description="First person to click wins..."
        )

        msg = await ctx.send(embed=embed)

        await asyncio.sleep(3.0)

        for _ in range(timer):
            embed.description = f"Starting in {3 - _} seconds..."
            await msg.edit(embed=embed)

            with contextlib.suppress(discord.Forbidden):
                await msg.clear_reactions()

            await asyncio.sleep(1)

        embed.description = f"CLICK CLICK CLICK"
        await msg.edit(embed=embed)

        def _check(r, u):
            return all((
                u != ctx.bot.user,
                str(r.emoji) == "\N{COOKIE}",
                not u.bot,
                r.message.id == msg.id
            ))

        await asyncio.sleep(0.10)

        with contextlib.suppress(discord.Forbidden):
            await msg.clear_reactions()

        start = time.perf_counter()
        try:
            await msg.add_reaction("\N{COOKIE}")
            reaction, user = await self.bot.wait_for("reaction_add", timeout=10.0, check=_check)
        except asyncio.TimeoutError:
            return await ctx.send("Damn, no one wanted the cookie...")

        end = time.perf_counter()

        if end - start <= 0.10:
            return await ctx.send("smh no cheating *tut* *tut* *tut*")

        embed.description = f"{user.mention} got it first in `{end - start:,.2f}` seconds \N{EYES}"
        await msg.edit(embed=embed)
        await self.handle_cookies(user)

    @cookieclick.command(name="leaderboard", aliases=["lb"])
    async def cookieclick_leaderboard(self, ctx):
        """Gives the leaderboard of all cookie clickers."""

        fields = await self.bot.pool.fetch("SELECT * FROM cookies order by cookies DESC LIMIT 100")

        desc = []

        for field in fields:
            user = self.bot.get_user(field["user_id"])
            desc.append(f"{user} - {field['cookies']} cookies")

        pages = menus.MenuPages(source=CookiesLBPage(
            ctx, desc), clear_reactions_after=True)
        await pages.start(ctx)

    @commands.command(aliases=["fban"])
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def fakeban(self, ctx, member: discord.Member, *, reason: str = "No Reason Provided."):
        """Fakes banning someone because that's funny, I think."""

        allowed_mentions = discord.AllowedMentions.none()
        await ctx.send(
            f"{member.mention} has been banned by {ctx.author} for: **{reason}**",
            allowed_mentions=allowed_mentions
        )

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def eject(
        self,
        ctx,
        text: typing.Union[discord.Member, str],
        colour: str,
        confirm: bool = True,
    ):
        """Ejects someone from the game.
        Usage: `{prefix}eject @kal#1806 red True`"""

        vac_api = vacefron.Client()
        text = text.name if type(text) == discord.Member else text

        if colour.lower() not in self.all_colours:
            return await ctx.send(
                f"List of available colours: {', '.join(self.all_colours)}"
            )

        if confirm is not True and confirm is not False:
            return await ctx.send("Confirm must be `true` or `false`")

        image = await vac_api.ejected(text, colour, confirm, confirm)
        image = await image.read(bytesio=True)

        await ctx.send(file=discord.File(image, filename="ejected.png"))
        await vac_api.close()

    @eject.error
    async def on_eject_error(self, ctx, error):
        if isinstance(error, vacefron.BadRequest):
            return await ctx.send(
                f"List of available colours: {', '.join(self.all_colours)}"
            )

    @commands.command(aliases=["rps"])
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def rockpaperscissors(self, ctx):
        """Play rock paper scissors with the bot!"""

        fmt = "What's your choice? Rock, Paper or Scissors..."
        embed = Embed.default(
            ctx,
            description=fmt
        )

        msg = await ctx.send(embed=embed)

        # Rock  # Paper  # Scissors
        emojis = ["\U0001faa8", "\U0001f4f0", "\U00002702"]

        bots_choice = random.choice(emojis)

        for _ in emojis:
            await msg.add_reaction(_)

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in emojis
                and reaction.message == msg
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=30.0, check=check
            )
        except asyncio.TimeoutError:
            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass

            embed.description = "You ran out of time!"
            await msg.edit(embed=embed)
        else:
            if str(reaction) == bots_choice:
                embed.description = f"You drew!"
                embed.colour = 0x0000FF

            elif str(reaction) == emojis[0] and bots_choice == emojis[2]:
                embed.description = f"You win! the bot chose {bots_choice}"
                embed.colour = 0x00FF00

            elif str(reaction) == emojis[1] and bots_choice == emojis[0]:
                embed.description = f"You win! the bot chose {bots_choice}"
                embed.colour = 0x00FF00

            elif str(reaction) == emojis[2] and bots_choice == emojis[1]:
                embed.description = f"You win! the bot chose {bots_choice}"
                embed.colour = 0x00FF00

            else:
                embed.description = f"You lost :( the bot chose {bots_choice}"
                embed.colour = 0xFF0000

            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass

            await msg.edit(embed=embed)

    @commands.command(aliases=["pp"])
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def penis(self, ctx, user: discord.Member = None):
        """Gives you your penis size."""

        user = user or ctx.author
        random.seed(user.id)
        size = 500 if user.id in self.bot.owner_ids else random.randint(0, 100)
        pp = f"8{'=' * size}D"
        await ctx.send(f"eh, that's alright: {pp}")

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def floof(self, ctx):
        """Get a random image of a cat or dog."""

        url = random.choice(
            ["https://some-random-api.ml/img/dog",
                "https://some-random-api.ml/img/cat"]
        )
        async with self.bot.session.get(url) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status.")
            data = await r.json()
            image = data["link"]

            embed = Embed.default(ctx)
            embed.set_image(url=image)
            await ctx.send(embed=embed)

    @commands.command(aliases=["ye"])
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def kanye(self, ctx):
        """Gives a random quote of Kanye West himself."""

        url = "https://api.kanye.rest/"
        async with self.bot.session.get(url) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status")
            data = await r.json()
            quote = data["quote"]

            embed = Embed.default(
                ctx,
                title=f'"{quote}" - Kanye West'
            )
            await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def nickme(self, ctx):
        """Gives you a random cool nickname."""

        url = "https://randomuser.me/api/?nat=us,dk,fr,gb,au,ca"
        async with self.bot.session.get(url) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status.")
            data = await r.json()
            name = data["results"][0]["name"]["first"]

            try:
                await ctx.author.edit(nick=name)
                await ctx.send(f"oo lala, {name} is such a beautiful name for you ❤")
            except discord.Forbidden:
                await ctx.send(
                    f"Uhh I couldn't change your name but I chose {name} for you anyways 😢"
                )

    @commands.command("8ball", aliases=["8b"])
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def _8ball(self, ctx, *, query: str):
        """Ask the oh so magic 8ball a question."""

        await ctx.send(f"🎱 {ctx.author.mention}, {random.choice(self._8ballResponse)}")

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def fact(self, ctx):
        """Gives you a cool random fact."""

        url = "https://uselessfacts.jsph.pl/random.json?language=en"
        async with self.bot.session.get(url) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status")
            data = await r.json()
            fact = data["text"]

            embed = Embed.default(
                ctx,
                description=fact
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Fun(bot, "🎉 Fun"))
