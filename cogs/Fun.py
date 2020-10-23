import asyncdagpi
from decouple import config
from discord.ext import commands

from utils import CustomContext, utils
from utils.CustomCog import BaseCog
from aiohttp import request
from asyncdagpi import ImageFeatures

import psutil
import asyncio
import discord
import typing
import random
import vacefron

standard_cooldown = 3.0


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
        self.pp_sizes = [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            100,
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

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def wanted(self, ctx, user: discord.Member = None):
        """Puts a members user avatar on a wanted poster."""

        dagpi = asyncdagpi.Client(config("DAGPI"))
        user = user or ctx.author
        url = str(user.avatar_url_as(static_format="png"))
        img = await dagpi.image_process(ImageFeatures.wanted(), url)
        img_file = discord.File(fp=img.image, filename=f"wanted.{img.format}")
        await ctx.send(content=f"Hands up **{user.name}!**", file=img_file)
        await dagpi.close()

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
        embed = utils.embed_message(message=fmt)

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
            await msg.clear_reactions()
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
    async def penis(self, ctx):
        """Gives you your penis size."""

        size = (
            100 if ctx.author.id == self.bot.owner_id else random.choice(
                self.pp_sizes)
        )
        pp = f"8{'=' * size}D"
        await ctx.send(f"ur pp size is {pp} 😎")

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def floof(self, ctx):
        """Get a random image of a cat or dog."""

        url = random.choice(
            ["https://some-random-api.ml/img/dog",
                "https://some-random-api.ml/img/cat"]
        )
        async with request("GET", url, headers={}) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status.")
            data = await r.json()
            image = data["link"]

            embed = utils.embed_message()
            embed.set_image(url=image)
            await ctx.send(embed=embed)

    @commands.command(aliases=["ye"])
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def kanye(self, ctx):
        """Gives a random quote of Kanye West himself."""

        url = "https://api.kanye.rest/"
        async with request("GET", url, headers={}) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status")
            data = await r.json()
            quote = data["quote"]

            embed = utils.embed_message(title=f'"{quote}" - Kanye West')
            await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def nickme(self, ctx):
        """Gives you a random cool nickname."""

        url = "https://randomuser.me/api/?nat=us,dk,fr,gb,au,ca"
        async with request("GET", url, headers={}) as r:
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

        sadness = ["kms", "kill myself", "i want to die", "depressed"]

        for word in sadness:
            if word in query.lower():
                return await ctx.send(
                    "If you're in a position where you're ever depressed or want to kill yourself, please talk to someone about it. You can contact the developer (kal#1806) if you'd like to :)"
                )

        await ctx.send(f"🎱 {ctx.author.mention}, {random.choice(self._8ballResponse)}")

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def fact(self, ctx):
        """Gives you a cool random fact."""

        url = "https://uselessfacts.jsph.pl/random.json?language=en"
        async with request("GET", url, headers={}) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status")
            data = await r.json()
            fact = data["text"]

            embed = utils.embed_message(message=fact)
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Fun(bot, "🎉 Fun"))
