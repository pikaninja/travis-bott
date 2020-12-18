import asyncio
import os

import KalDiscordUtils
import psutil
from discord.ext import commands, menus

import utils


class Beta(utils.BaseCog, name="utils", command_attrs=dict(hidden=True)):
    """I put beta commands here I guess."""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name

    @commands.group(aliases=["b"], invoke_without_command=True)
    async def beta(self, ctx: utils.CustomContext):
        """Some beta commands that are not ready for release quite yet."""

        await ctx.send_help(ctx.command)

    @beta.command(name="info", aliases=["about"])
    async def beta_info(self, ctx: utils.CustomContext):
        """Gather some information on the bot."""

        embed = KalDiscordUtils.Embed.default(ctx)
        embed.set_thumbnail(
            url=str(self.bot.user.avatar_url_as(format="png",
                                                static_format="png",
                                                size=1024))
        )

        developer = [str(self.bot.get_user(x)) for x in self.bot.owner_ids][0]
        guild_count = len(self.bot.guilds)
        member_count = sum(g.member_count for g in self.bot.guilds)

        process = psutil.Process(os.getpid())
        memory_used = process.memory_info().rss / 1024 ** 2
        memory_info = psutil.virtual_memory()

        cpu_percentage = psutil.cpu_percent()

        fields = [
            ["Invite", f"[Invite the bot here!]({self.bot.invite_url})", True],
            ["Need Support?",
                f"[Join the support server here]({self.bot.support_url})", True],
            ["Want to see the source?",
                f"[Click here to view it]({self.bot.github_url})", True],
            ["Current Ping", f"{(self.bot.latency * 1000):,.2f} ms", True],
            ["Developer", f"{developer}", True],
            ["Guild Count", f"{guild_count}", True],
            ["User Count", f"{member_count:,}", True],
            ["Memory usage",
                f"{int(memory_used):,}/{int(memory_info.total / 1024 ** 2):,} MB", True],
            ["CPU usage", f"{cpu_percentage}%", True],
        ]

        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Beta(bot, show_name="\N{HAMMER AND WRENCH} Beta"))
