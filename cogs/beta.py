"""
Beta commands that are used for testing
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
import logging

import discord
from jishaku.codeblocks import codeblock_converter
from discord.ext import commands

import utils


class Beta(commands.Cog, name="beta", command_attrs=dict(hidden=True)):
    """I put beta commands here I guess."""

    def __init__(self, bot):
        self.bot: utils.MyBot = bot
        self.show_name = "\N{HAMMER AND WRENCH} Beta"
        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

    @commands.group(aliases=["b"], invoke_without_command=True)
    async def beta(self, ctx: utils.CustomContext):
        """Some beta commands that are not ready for release quite yet."""

        await ctx.send_help(ctx.command)

    # @beta.command(name="neofetch")
    # async def beta_neofetch(self, ctx: utils.CustomContext):
    #     """Shows an output similar to Neofetch about the bots system."""

    # @beta.command(name="duckduckgo")
    # async def beta_duckduckgo(self, ctx: utils.CustomContext, *, query: str):
    #     """Searches duckduckgo with a given query."""
    #
    #     url = "http://duckduckgo.com/html/?q=" + query
    #     async with self.bot.session.get(url) as response:
    #         # if response != 200:
    #         #     return await ctx.send("Something messed up lol")
    #
    #         soup = BeautifulSoup(await response.text(), features="lxml")
    #         results = soup.find_all(
    #             "a", attrs={"class": "result__a"}, href=True)
    #         result = results[0]
    #
    #         link = f"https:{result.get('href')}"
    #         title = result.get_text()
    #
    #         embed = KalDiscordUtils.Embed.default(ctx)
    #         embed.title = title
    #         embed.url = link
    #
    #         await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Beta(bot))
