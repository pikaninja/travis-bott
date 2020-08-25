from decouple import config
from discord.ext import commands

from utils import CustomContext, utils
from aiohttp import request

import psutil
import discord
import typing
import random

standard_cooldown = 3.0

class Fun(commands.Cog, name="🎉 Fun"):
    """Fun Commands"""
    def __init__(self, bot):
        self.bot = bot
        self._8ballResponse = ['It is certain', 'It is decidedly so', 'Without a doubt', 'Yes, definitely',
                               'You may rely on it', 'As I see it, yes', 'Most likely', 'Outlook good',
                               'Signs point to yes', 'Yes', 'Reply hazy, try again', 'Ask again later',
                               'Better not tell you now', 'Cannot predict now', 'Concentrate and ask again',
                               "Don't bet on it", 'My reply is no', 'My sources say no', 'Outlook not so good',
                               'Very doubtful']
        self.pp_sizes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                         1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                         1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                         1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                         1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                         100]

    @commands.command(aliases=["pp"])
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def penis(self, ctx):
        """Gives you your penis size."""

        size = random.choice(self.pp_sizes)
        pp = f"8{'=' * size}D"
        await ctx.send(f"ur pp size is {pp} 😎")

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def floof(self, ctx):
        """Get a random image of a cat or dog."""

        url = random.choice(["https://some-random-api.ml/img/dog", "https://some-random-api.ml/img/cat"])
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

            embed = utils.embed_message(title=f"\"{quote}\" - Kanye West")
            await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def nickme(self, ctx):
        """Gives you a random cool nickname."""

        url = "https://randomuser.me/api/?nat=us,dk,fr,gb,au,ca"
        async with request("GET", url, headers={}) as r:
            if r.status != 200:
                return await ctx.send(f"The API return a {r.status} status.")
            data = await r.json()
            name = data["results"][0]["name"]["first"]

            try:
                await ctx.author.edit(nick=name)
                await ctx.send(f"oo lala, {name} is such a beautiful name for you ❤")
            except discord.Forbidden:
                await ctx.send(f"Uhh I couldn't change your name but I chose {name} for you anyways 😢")

    @commands.command("8ball", aliases=["8b"])
    @commands.cooldown(1, standard_cooldown, commands.BucketType.member)
    async def _8ball(self, ctx, *, query: str):
        """Ask the oh so magic 8ball a question."""

        sadness = ["kms", "kill myself", "i want to die", "depressed"]
        
        for word in sadness:
            if word in query.lower():
                return await ctx.send("If you're in a position where you're ever depressed or want to kill yourself, please talk to someone about it. You can contact the developer (kal#1806) if you'd like to :)")
        
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
    bot.add_cog(Fun(bot))