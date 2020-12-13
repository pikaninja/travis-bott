import functools
import random
import re
import typing
from io import BytesIO

import KalDiscordUtils
import asyncdagpi
import discord
from asyncdagpi import ImageFeatures
from decouple import config
from discord.ext import commands
from polaroid.polaroid import Image
from wand.color import Color
from wand.image import Image as WandImage

import utils


async def do_dagpi_stuff(user, feature) -> discord.File:
    dagpi = asyncdagpi.Client(config("DAGPI"))
    url = str(user.avatar_url_as(static_format="png"))
    img = await dagpi.image_process(feature, url)
    img_file = discord.File(fp=img.image, filename=f"image.{img.format}")
    await dagpi.close()
    return img_file


class ImageOrMember(commands.Converter):
    async def convert(self, ctx: utils.CustomContext, argument: str):
        try:
            member_converter = commands.MemberConverter()
            member = await member_converter.convert(ctx, argument)

            asset = member.avatar_url_as(static_format="png",
                                         format="png",
                                         size=512)
            image = await asset.read()

            return image

        except (commands.MemberNotFound, TypeError):

            try:
                url_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
                emoji_regex = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"

                if re.match(url_regex, argument):
                    async with ctx.bot.session.get(argument) as response:
                        image = await response.read()
                        return image

                elif re.match(emoji_regex, argument):
                    emoji_converter = commands.EmojiConverter()
                    emoji = await emoji_converter.convert(ctx, argument)

                    asset = emoji.url
                    image = await asset.read()

                    return image
            except TypeError:
                return None

        return None


async def get_image(ctx: utils.CustomContext, argument: str):
    """This coincides with ImageOrMember to allow me to use attachments."""

    converter = ImageOrMember()
    image = await converter.convert(ctx, argument)
    if image is None:
        if ctx.message.attachments:
            asset = ctx.message.attachments[0]
            image = await asset.read()
            return image
        else:
            asset = ctx.author.avatar_url_as(static_format="png",
                                             format="png",
                                             size=512)
            image = await asset.read()
            return image
    else:
        return image


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
        if image_one.size != (1024, 1024):
            image_one.resize(1024, 1024, 5)

        image_two = Image(image_two_bytes)
        if image_two.size != (256, 256):
            image_two.resize(256, 256, 5)

        facetime_buttons = Image("./data/facetimebuttons.png")
        facetime_buttons.resize(1024, 1024, 5)

        image_one.watermark(image_two, 15, 15)
        image_one.watermark(facetime_buttons, 0, 390)
        io_bytes = BytesIO(image_one.save_bytes())

        return io_bytes

    @staticmethod
    def magik(image: BytesIO):
        with WandImage(file=image) as img:
            img.liquid_rescale(width=int(img.width * 0.5),
                               height=int(img.height * 0.5),
                               delta_x=random.randint(1, 2),
                               rigidity=0)

            img.liquid_rescale(width=int(img.width * 1.5),
                               height=int(img.height * 1.5),
                               delta_x=random.randrange(1, 3),
                               rigidity=0)

            buffer = BytesIO()
            img.save(file=buffer)

        buffer.seek(0)
        return buffer

    @staticmethod
    def floor(image: BytesIO):  # https://github.com/linKhehe/Zane fank u link
        with WandImage(file=image) as img:
            img.resize(256, 256)
            img.matte_color = Color("BLACK")
            img.virtual_pixel = "tile"
            args = (0, 0, 77, 153,
                    img.height, 0, 179, 153,
                    0, img.width, 51, 255,
                    img.height, img.width, 204, 255)
            img.distort("perspective", args)

            buffer = BytesIO()
            img.save(file=buffer)

        buffer.seek(0)
        return buffer

    @staticmethod
    def chroma(image: BytesIO):
        with WandImage(file=image) as img:
            img.function("sinusoid", [1.5, -45, 0.2, 0.60])

            buffer = BytesIO()
            img.save(file=buffer)

        buffer.seek(0)
        return buffer

    @staticmethod
    def swirl(image: BytesIO, degrees: int = 90):
        with WandImage(file=image) as img:
            if degrees > 360:
                degrees = 360
            elif degrees < -360:
                degrees = -360
            else:
                degrees = degrees

            img.swirl(degree=degrees)

            buffer = BytesIO()
            img.save(file=buffer)

        buffer.seek(0)
        return buffer


class ImageManipulation(utils.BaseCog, name="imagemanipulation"):
    """Image Manipulation"""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def swirl(self, ctx: utils.CustomContext, degrees: int = 90, what=None):
        """Adds a swirl affect to a given image."""

        async with ctx.timeit:
            async with ctx.typing():
                image = await get_image(ctx, what)
                buffer = BytesIO(image)

                func = functools.partial(Manipulation.swirl, buffer, degrees)
                buffer = await self.bot.loop.run_in_executor(None, func)

                embed = KalDiscordUtils.Embed.default(ctx)
                file = discord.File(fp=buffer, filename="chroma.png")
                embed.set_image(url="attachment://chroma.png")

                await ctx.send(
                    file=file,
                    embed=embed
                )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def chroma(self, ctx: utils.CustomContext, what=None):
        """Adds a chroma gamma affect to a given image."""

        async with ctx.timeit:
            async with ctx.typing():
                image = await get_image(ctx, what)
                buffer = BytesIO(image)
                func = functools.partial(Manipulation.chroma, buffer)
                buffer = await self.bot.loop.run_in_executor(None, func)

                embed = KalDiscordUtils.Embed.default(ctx)
                file = discord.File(fp=buffer, filename="chroma.png")
                embed.set_image(url="attachment://chroma.png")

                await ctx.send(
                    file=file,
                    embed=embed
                )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def floor(self, ctx: utils.CustomContext, what=None):
        """Puts an image on a floor."""

        async with ctx.timeit:
            async with ctx.typing():
                image = await get_image(ctx, what)
                buffer = BytesIO(image)

                func = functools.partial(Manipulation.floor, buffer)
                buffer = await self.bot.loop.run_in_executor(None, func)

                embed = KalDiscordUtils.Embed.default(ctx)
                file = discord.File(fp=buffer, filename="floor.png")
                embed.set_image(url="attachment://floor.png")

                await ctx.send(
                    file=file,
                    embed=embed
                )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def magik(self, ctx: utils.CustomContext, what: typing.Optional[str]):
        """I'm pretty sure you've seen this command before"""

        async with ctx.timeit:
            async with ctx.typing():
                what = await get_image(ctx, what)
                buffer = BytesIO(what)

                func = functools.partial(Manipulation.magik, buffer)
                buffer = await self.bot.loop.run_in_executor(None, func)

                embed = KalDiscordUtils.Embed.default(ctx)
                file = discord.File(buffer, filename="magik.png")
                embed.set_image(url="attachment://magik.png")

                await ctx.send(file=file,
                               embed=embed)

    @commands.command(aliases=["ft"])
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def facetime(self, ctx: utils.CustomContext, what: str):
        """Facetime with another user or even an image if you're really that lonely, I guess."""

        async with ctx.timeit:
            async with ctx.typing():
                author_image = await ctx.author.avatar_url_as(static_format="png", size=1024).read()
                what = await get_image(ctx, what)

                func = functools.partial(
                    Manipulation.facetime, what, author_image)
                image_bytes = await self.bot.loop.run_in_executor(None, func)

                embed = KalDiscordUtils.Embed.default(ctx)
                file = discord.File(image_bytes, filename="facetime.png")
                embed.set_image(url="attachment://facetime.png")

                await ctx.send(
                    file=file,
                    embed=embed
                )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def brighten(self, ctx: utils.CustomContext, what: typing.Optional[str], amount: int = 50):
        """Brightens a given picture or your own or even someone else's profile picture by a given amount"""

        async with ctx.timeit:
            async with ctx.typing():
                what = await get_image(ctx, what)

                func = functools.partial(
                    Manipulation.brighten_image, what, amount)
                image_bytes = await self.bot.loop.run_in_executor(None, func)

                embed = KalDiscordUtils.Embed.default(ctx)
                file = discord.File(image_bytes, filename="brightened.png")
                embed.set_image(url="attachment://brightened.png")

                await ctx.send(
                    file=file,
                    embed=embed
                )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def solarize(self, ctx: utils.CustomContext, what: typing.Optional[str]):
        """Solarizes your own or someone else's profile picture or even a given picture."""

        async with ctx.timeit:
            async with ctx.typing():
                what = await get_image(ctx, what)

                func = functools.partial(Manipulation.solarize_image, what)
                image_bytes = await self.bot.loop.run_in_executor(None, func)

                embed = KalDiscordUtils.Embed.default(ctx)
                file = discord.File(image_bytes, filename="solarize.png")
                embed.set_image(url="attachment://solarize.png")

                await ctx.send(
                    file=file,
                    embed=embed
                )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def wanted(self, ctx: utils.CustomContext, user: discord.Member = None):
        """Puts a members user avatar on a wanted poster."""

        async with ctx.timeit:
            async with ctx.typing():
                user = user or ctx.author
                img_file = await do_dagpi_stuff(user, ImageFeatures.wanted())
                await ctx.send(content=f"Hands up **{user.name}!**", file=img_file)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def colours(self, ctx: utils.CustomContext, user: discord.Member = None):
        """Gives you the top 5 colours of your own or another persons profile picture."""

        async with ctx.timeit:
            async with ctx.typing():
                user = user or ctx.author
                img_file = await do_dagpi_stuff(user, ImageFeatures.colors())
                await ctx.send(
                    f"Top 5 Colours for {user}",
                    file=img_file
                )

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def pixelate(self, ctx: utils.CustomContext, user: discord.Member = None):
        """Pixelates someones profile picture"""

        async with ctx.timeit:
            async with ctx.typing():
                user = user or ctx.author
                img_file = await do_dagpi_stuff(user, ImageFeatures.pixel())
                await ctx.send(file=img_file)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def polaroid(self, ctx: utils.CustomContext, user: discord.Member = None):
        """Puts someones profile picture in a polaroid"""

        async with ctx.timeit:
            async with ctx.typing():
                user = user or ctx.author
                img_file = await do_dagpi_stuff(user, ImageFeatures.polaroid())
                await ctx.send(
                    "*Look at this photograph*",
                    file=img_file
                )


def setup(bot):
    bot.add_cog(ImageManipulation(bot, show_name="👁️ Image Manipulation"))
