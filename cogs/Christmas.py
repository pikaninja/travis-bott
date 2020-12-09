import asyncio
import datetime
import random

import KalDiscordUtils
import discord
from discord.ext import commands

from utils.CustomBot import MyBot
from utils.CustomCog import BaseCog
from utils.CustomContext import CustomContext


class Christmas(BaseCog, name="christmas"):
    """Christmas Stuff"""

    def __init__(self, bot, show_name):
        self.bot: MyBot = bot
        self.show_name = show_name

    @commands.command()
    async def howlong(self, ctx: CustomContext):
        """Gives you how long it is until Christmas."""

        time = datetime.datetime(year=2020, month=12, day=25)
        formatted_time = KalDiscordUtils.format_time(time)
        embed = KalDiscordUtils.Embed.default(
            ctx,
            title=f"{formatted_time['precise']} until {formatted_time['date']}"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["sbf"])
    async def snowballfight(self, ctx: CustomContext, user: discord.Member):
        """Starts a snowball fight with someone!"""

        if user == ctx.author:
            return await ctx.send("You can't fight yourself...")

        currently_fighting = True
        peoples_hp = {
            ctx.author: 100,
            user: 100
        }
        turn = 0

        while currently_fighting:
            if turn == 0:
                damage = random.randint(1, 25)
                peoples_hp[user] -= damage
                hp_now = peoples_hp[user] if peoples_hp[user] > 0 else 0
                await ctx.send(
                    f"{ctx.author} throws a snowball at {user} hitting them for {damage} HP\n"
                    f"{user} is now at {hp_now} HP",
                    delete_after=5
                )
                turn = 1

            elif turn == 1:
                damage = random.randint(1, 25)
                peoples_hp[ctx.author] -= damage
                hp_now = peoples_hp[ctx.author] if peoples_hp[ctx.author] > 0 else 0
                await ctx.send(
                    f"{user} throws a snowball at {ctx.author} hitting them for {damage} HP\n"
                    f"{ctx.author} is now at {hp_now} HP",
                    delete_after=5
                )
                turn = 0

            elif turn == 3:
                pass

            if peoples_hp[ctx.author] <= 0:
                currently_fighting = False
                turn = 3
                winner = user
            if peoples_hp[user] <= 0:
                currently_fighting = False
                turn = 3
                winner = ctx.author

            await asyncio.sleep(random.choice([1, 2]))

        await ctx.send(f"{winner} won with {peoples_hp[winner]} HP left!")


def setup(bot):
    bot.add_cog(Christmas(bot, show_name="❄ Christmas"))
