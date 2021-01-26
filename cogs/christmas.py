"""
Christmas commands for festivity
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


import asyncio
import datetime
import logging
import random

import discord

from discord.ext import commands

from utils.embed import Embed

import utils


class Christmas(commands.Cog, name="christmas"):
    """Christmas Stuff"""

    def __init__(self, bot):
        self.bot: utils.MyBot = bot
        self.show_name = "\N{SNOWFLAKE} Christmas"
        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

    @commands.command()
    async def howlong(self, ctx: utils.CustomContext):
        """Gives you how long it is until Christmas."""

        current_year = datetime.datetime.utcnow().year
        time = datetime.datetime(year=current_year, month=12, day=25)
        formatted_time = utils.format_time(time)
        embed = Embed.default(
            ctx,
            title=f"{formatted_time['precise']} until {formatted_time['date']}"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["sbf"])
    @commands.max_concurrency(1, commands.BucketType.channel)
    async def snowballfight(self, ctx: utils.CustomContext, user: discord.Member):
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
    bot.add_cog(Christmas(bot))
