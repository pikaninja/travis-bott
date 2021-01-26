import os
import psutil
import utils
import platform
from discord.ext import commands


class DebugCog(commands.Cog):
    def __init__(self, bot):
        self.bot: utils.MyBot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.group(aliases=["dbg"], invoke_without_command=True)
    async def debug(self, ctx: utils.CustomContext):
        """Base Command for the Debug cog."""

        description = list()
        description.append(
            f"This bot runs on Python {platform.python_version()} `[{platform.python_compiler()}]`\n")

        process = psutil.Process(os.getpid())
        memory_used = process.memory_info().rss / 1024 ** 2
        memory_info = psutil.virtual_memory()

        memory_fmt = (
            "The bot is currently using: "
            f"{memory_used:,.2f}/{memory_info.total / 1024 ** 2:,.2f} MB of memory"
        )
        description.append(memory_fmt)

        can_see_fmt = (
            "The bot can currently see: "
            f"{sum(g.member_count for g in self.bot.guilds):,} Members in {len(self.bot.guilds)} Guilds."
        )
        description.append(can_see_fmt)

        with ctx.embed() as embed:
            embed.description = "\n".join(description)
            await ctx.send(embed=embed)

    @debug.command(name="timeit")
    async def debug_timeit(self, ctx: utils.CustomContext, *command: str):
        """Times how long it takes to run a command."""

        command, args = command[0], command[1:]
        get_cmd = self.bot.get_command(command)
        async with ctx.timeit:
            await get_cmd(ctx, *args)


def setup(bot):
    bot.add_cog(DebugCog(bot))
