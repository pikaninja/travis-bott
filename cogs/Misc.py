from decouple import config
from discord.ext import commands

from utils import utils

class Misc(commands.Cog, name="💫 Misc"):
    """Miscellaneous Commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def suggest(self, ctx, *, suggestion: str):
        """Send a suggestion to the bot developer."""

        msg = f"**Suggestion from {ctx.author} ({ctx.author.id}) at {ctx.message.created_at}**\n{suggestion}"
        await ctx.bot.get_channel(710978375426244729).send(msg)
        await ctx.thumbsup()

    @commands.command()
    async def support(self, ctx):
        """Gives a link to the support server."""

        await ctx.send("If you need help with the bot please join the support server:\n" + \
                       f"{config('SUPPORT_LINK')}")

    @commands.command()
    async def uptime(self, ctx):
        """Get the bots uptime."""

        await ctx.send(f"Uptime: {self.bot.get_uptime()}")

    @commands.command(aliases=["git", "code"])
    async def github(self, ctx):
        """Sends the bots github repo"""

        await ctx.author.send(f"{config('GITHUB_LINK')}")
        await ctx.thumbsup()

def setup(bot):
    bot.add_cog(Misc(bot))