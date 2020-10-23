from discord.ext import commands


class BaseCog(commands.Cog):
    def __init__(self, bot, show_name):
        super().__init__()
        self.bot = bot
        self.show_name = show_name
