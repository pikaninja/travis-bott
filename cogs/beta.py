from discord.ext import commands

import utils


class Beta(utils.BaseCog, name="beta", command_attrs=dict(hidden=True)):
    """I put beta commands here I guess."""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name

    @commands.group(aliases=["b"], invoke_without_command=True)
    async def beta(self, ctx: utils.CustomContext):
        """Some beta commands that are not ready for release quite yet."""

        await ctx.send_help(ctx.command)


def setup(bot):
    bot.add_cog(Beta(bot, show_name="\N{HAMMER AND WRENCH} Beta"))
