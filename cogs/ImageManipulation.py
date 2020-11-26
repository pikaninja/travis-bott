import functools
import time
import typing
from io import BytesIO

import KalDiscordUtils
import asyncdagpi
import discord
from asyncdagpi import ImageFeatures
from decouple import config
from discord.ext import commands
from polaroid.polaroid import Image

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

    class Manipulation:

        @staticmethod
        def solarize_image(b: bytes):
            image = Image(b)
            image.solarize()
            save_bytes = image.save_bytes()
            io_bytes = BytesIO(save_bytes)

            return io_bytes

        @staticmethod
        def brighten_image(b: bytes, amount: int):
            image = Image(b)
            image.brighten(amount)
            save_bytes = image.save_bytes()
            io_bytes = BytesIO(save_bytes)

            return io_bytes

        @staticmethod
        def facetime(image_one_bytes: bytes,
                     image_two_bytes: bytes):

            image_one = Image(image_one_bytes)
            if image_one.width < 1024 and image_one.height < 1024:
                image_one.resize(1024, 1024, 1)

            if image_one.width > 1024 and image_one.height > 1024:
                image_one.resize(1024, 1024, 1)

            image_two = Image(image_two_bytes)
            if image_two.width < 256 and image_two.height < 256:
                image_two.resize(256, 256, 1)

            if image_two.width > 256 and image_two.height > 256:
                image_two.resize(256, 256, 1)

            facetime_buttons = Image("./data/facetimebuttons.png")
            facetime_buttons.resize(1024, 1024, 1)

            image_one.watermark(image_two, 15, 15)
            image_one.watermark(facetime_buttons, 0, 390)
            io_bytes = BytesIO(image_one.save_bytes())

            return io_bytes

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def facetime(self, ctx, user: discord.Member):
        """Facetime with another user."""

        start_time = time.perf_counter()
        author_image = await ctx.author.avatar_url_as(static_format="png", size=1024).read()
        user_image = await user.avatar_url_as(static_format="png", size=256).read()

        func = functools.partial(self.Manipulation.facetime, user_image, author_image)
        image_bytes = await self.bot.loop.run_in_executor(None, func)

        file = discord.File(image_bytes, filename="facetime.png")
        embed = KalDiscordUtils.Embed.default(
            ctx,
            title=f"yoooo y'all are facetiming"
        )
        embed.set_image(url="attachment://facetime.png")
        end_time = time.perf_counter()

        time_taken = f"{end_time - start_time:,.2f}"
        await ctx.send(
            content=f"Finished processing in: `{time_taken} seconds`",
            file=file,
            embed=embed
        )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def brighten(self, ctx, user: typing.Optional[discord.Member] = None, amount: int = 50):
        """Brightens your own or someone else's profile picture by a given amount"""

        start_time = time.perf_counter()
        user = user or ctx.author
        user_image = await user.avatar_url_as(static_format="png").read()

        func = functools.partial(self.Manipulation.brighten_image, user_image, amount)
        image_bytes = await self.bot.loop.run_in_executor(None, func)

        file = discord.File(image_bytes, filename="brightened.png")
        embed = KalDiscordUtils.Embed.default(
            ctx,
            title=f"Brightened profile picture for: {user.name}"
        )
        embed.set_image(url="attachment://brightened.png")
        end_time = time.perf_counter()

        time_taken = f"{end_time - start_time:,.2f}"
        await ctx.send(
            content=f"Finished processing in: `{time_taken} seconds`",
            file=file,
            embed=embed
        )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def solarize(self, ctx, user: discord.Member = None):
        """Solarizes your own or someone else's profile picture"""

        start_time = time.perf_counter()
        user = user or ctx.author
        user_image = await user.avatar_url_as(static_format="png").read()

        func = functools.partial(self.Manipulation.solarize_image, user_image)
        image_bytes = await self.bot.loop.run_in_executor(None, func)

        file = discord.File(image_bytes, filename="solarize.png")
        embed = KalDiscordUtils.Embed.default(
            ctx,
            title=f"Solarized profile picture for: {user.name}"
        )
        embed.set_image(url="attachment://solarize.png")
        end_time = time.perf_counter()

        time_taken = f"{end_time - start_time:,.2f}"
        await ctx.send(
            content=f"Finished processing in: `{time_taken} seconds`",
            file=file,
            embed=embed
        )

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
