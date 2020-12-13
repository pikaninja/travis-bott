from discord.ext import commands

import utils

class Tags(utils.BaseCog, name="tags"):
    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name

    @commands.group()
    async def tag(self):
        """The base command for everything to do with tags."""

def setup(bot):
    bot.add_cog(Tags(bot, "\N{NOTEBOOK WITH DECORATIVE COVER} Tags"))