import asyncdagpi
import discord
from asyncdagpi import ImageFeatures
from decouple import config
from discord.ext import commands

from utils.CustomCog import BaseCog


async def do_dagpi_stuff(user, feature) -> discord.File:
    dagpi = asyncdagpi.Client(config("DAGPI"))
    url = str(user.avatar_url_as(static_format="png"))
    img = await dagpi.image_process(feature, url)
    img_file = discord.File(fp=img.image, filename=f"image.{img.format}")
    await dagpi.close()
    return img_file


class ImageManipulation(BaseCog, name="imagemanipulation"):
    """Image Manipulation"""

    def __init__(self, bot, show_name):
        self.bot = bot
        self.show_name = show_name

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def wanted(self, ctx, user: discord.Member = None):
        """Puts a members user avatar on a wanted poster."""

        user = user or ctx.author
        img_file = await do_dagpi_stuff(user, ImageFeatures.wanted())
        await ctx.send(content=f"Hands up **{user.name}!**", file=img_file)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def colours(self, ctx, user: discord.Member = None):
        """Gives you the top 5 colours of your own or another persons profile picture."""

        user = user or ctx.author
        img_file = await do_dagpi_stuff(user, ImageFeatures.colors())
        await ctx.send(
            f"Top 5 Colours for {user}",
            file=img_file
        )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def pixelate(self, ctx, user: discord.Member = None):
        """Pixelates someones profile picture"""

        user = user or ctx.author
        img_file = await do_dagpi_stuff(user, ImageFeatures.pixel())
        await ctx.send(file=img_file)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def polaroid(self, ctx, user: discord.Member = None):
        """Puts someones profile picture in a polaroid"""

        user = user or ctx.author
        img_file = await do_dagpi_stuff(user, ImageFeatures.polaroid())
        await ctx.send(
            "*Look at this photograph*",
            file=img_file
        )


def setup(bot):
    bot.add_cog(ImageManipulation(bot, show_name="👁️ Image Manipulation"))