import asyncio
import os

import KalDiscordUtils
import discord
import psutil
from discord.ext import commands, menus, flags

import utils


class GiveawayQuestions:

    @staticmethod
    async def what_channel(ctx: utils.CustomContext, name_or_id: str):
        converter = commands.TextChannelConverter()

        try:
            channel = await converter.convert(ctx, name_or_id)
        except commands.ChannelNotFound:
            raise commands.BadArgument("I couldn't find that channel! You must restart the interactive giveaway.")

        return channel, "channel"


class Beta(utils.BaseCog, name="beta", command_attrs=dict(hidden=True)):
    """I put beta commands here I guess."""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name

    @commands.group(aliases=["b"], invoke_without_command=True)
    async def beta(self, ctx: utils.CustomContext):
        """Some beta commands that are not ready for release quite yet."""

        await ctx.send_help(ctx.command)

    @beta.command(name="startgiveaway", aliases=["sgw"])
    @commands.has_permissions(manage_guild=True)
    async def bet_sgw(self, ctx: utils.CustomContext):
        """Starts an interactive dialogue to set up a giveaway."""

        questions = {
            "What channel would you like the giveaway to be in?": GiveawayQuestions.what_channel,
        }

        what_is_needed = {
            "channel": None,
            "time_end": None,
            "prize": None,
            "role_needed": None
        }

        for question, func in questions.keys():
            await ctx.send(question)
            try:
                response = await self.bot.wait_for("message",
                                                   timeout=30.0,
                                                   check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            except asyncio.TimeoutError:
                return await ctx.send("You did not reply in time!")
            else:
                get_channel, what_thing = func(ctx, response.content)
                what_is_needed[what_thing] = get_channel

        print(what_is_needed)


def setup(bot):
    bot.add_cog(Beta(bot, show_name="\N{HAMMER AND WRENCH} Beta"))
