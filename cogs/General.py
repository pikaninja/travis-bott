from decouple import config
from discord.ext import commands

from utils import utils

import psutil
import discord
import typing
import random
import numexpr
import re

class General(commands.Cog, name="🤖 General"):
    """General Commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["randomcolor", "rcolour", "rcolor"])
    async def randomcolour(self, ctx):
        """Gives a random colour."""

        r_colour = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        rgb_to_hex = "#%02x%02x%02x" % r_colour
        colour_representation = f"https://some-random-api.ml/canvas/colorviewer?hex={rgb_to_hex[1:]}"
        embed = utils.embed_message(title="Generated Colour",
                                    colour=discord.Colour.from_rgb(r_colour[0], r_colour[1], r_colour[2]))
        embed.set_thumbnail(url=colour_representation)
        embed.add_field(name="Hex", value=f"{rgb_to_hex}", inline=False)
        embed.add_field(name="RGB", value=f"{r_colour}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["color"])
    async def colour(self, ctx, colour: str):
        """Shows a representation of a given colour"""

        hex_regex = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"

        if not re.match(hex_regex, colour):
            return await ctx.send("The colour must be a properly formed **hex** colour.")

        colour_representation = f"https://some-random-api.ml/canvas/colorviewer?hex={colour[1:]}"
        hex_to_rgb = utils.hex_to_rgb(colour[1:])
        embed = utils.embed_message(colour=discord.Colour.from_rgb(hex_to_rgb[0], hex_to_rgb[1], hex_to_rgb[2]))
        embed.set_thumbnail(url=colour_representation)
        embed.add_field(name="Hex", value=f"{colour}", inline=False)
        embed.add_field(name="RGB", value=f"{hex_to_rgb}", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["av"])
    async def avatar(self, ctx, member: typing.Optional[discord.Member]):
        """Get your own or another persons avatar."""

        if not member:
            member = ctx.author
        
        embed = utils.embed_message()
        embed.set_author(name=member, icon_url=member.avatar_url)
        embed.set_image(url=member.avatar_url_as(static_format="png", size=1024))
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["latency"])
    async def ping(self, ctx):
        """Get the bots ping."""

        embed = utils.embed_message(message=f"**{int(ctx.bot.latency * 1000)} ms**")
        embed.set_author(name="Travis Bott's Latency:", icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)
    
    @commands.command()
    async def info(self, ctx):
        """Get basic info on the bot."""

        invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot"

        cpu_percentage = psutil.cpu_percent()
        mem_used = (psutil.virtual_memory().total - psutil.virtual_memory().available) / 1000000
        total_mem = psutil.virtual_memory().total / 1000000

        embed = utils.embed_message(title=f"Info about {self.bot.user.name}",
                                    footer_text=f"Bot Version: {self.bot.version} | D.py Version: {discord.__version__}")
        embed.add_field(name="Invite the bot", value=f"[Here]({invite_link})")
        embed.add_field(name="GitHub", value=f"[Here]({config('GITHUB_LINK')})")
        embed.add_field(name="Support server", value=f"[Here]({config('SUPPORT_LINK')})")
        embed.add_field(name="Ping", value=f"{round(self.bot.latency * 1000)} ms")
        embed.add_field(name="Memory", value=f"{round(mem_used)} MB / {round(total_mem)} MB")
        embed.add_field(name="CPU", value=f"{cpu_percentage}%")
        embed.add_field(name="Creator", value=f"{config('DEVELOPER')}")
        embed.add_field(name="Currently in", value=f"{len(self.bot.guilds)} servers")
        embed.add_field(name="Current prefix", value=f"`{ctx.prefix}`")

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))