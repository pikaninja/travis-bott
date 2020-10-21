import discord
from discord.ext import commands

from utils.CustomContext import CustomContext

class ChunkGuildOnCmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx: CustomContext):
        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)

def setup(bot):
    bot.add_cog(ChunkGuildOnCmd(bot))