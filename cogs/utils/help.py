from discord.ext import commands
from utils.customhelp import CustomHelp


class Help(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command.cog = self
        bot.help_command = CustomHelp(
            command_attrs={"hidden": True, "aliases": ["h"]})

    def cog_unload(self):
        self.bot.help_command = self._original_help_command


def setup(bot):
    bot.add_cog(Help(bot))