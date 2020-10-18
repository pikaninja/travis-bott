import discord
from discord.ext import commands

from utils.Paginator import Paginator
from utils import utils

class HelpCommand(commands.HelpCommand):

    async def filter_commands(self, commands, *, sort=False, key=None):
        """Custom version of filter commands due to me not liking the way it filters out cmds that are permission based."""

        if sort and key is None:
            key = lambda c: c.name

        iterator = commands if self.show_hidden else filter(lambda c: not c.hidden, commands)

        if not self.verify_checks:
            # if we do not need to verify the checks then we can just
            # run it straight through normally without using await.
            return sorted(iterator, key=key) if sort else list(iterator)

        ret = []
        for cmd in iterator:
            ret.append(cmd)

        if sort:
            ret.sort(key=key)
        return ret

    # This function triggers when somone type `<prefix>help`
    async def send_bot_help(self, mapping):
        ctx = self.context

        embed_list = []

        for cog, commands in mapping.items():
            try:
                if getattr(cog, "is_in_help") == True:
                    embed = utils.embed_message()
                    name = "No Category" if cog is None else cog.qualified_name
                    filtered = await self.filter_commands(commands, sort=True)
                    if filtered:
                        all_cmds = "\n\n".join(f"**{c.name}**:\n*{c.help}*" for c in commands)
                        if cog and cog.description:
                            embed.title = f"{self.clean_prefix}help {cog.name}"
                            embed.description = cog.description
                    
                    embed_list.append(embed)
            except AttributeError:
                pass

        p = Paginator(embed_list, clear_reactions=True)
        await p.paginate(ctx)

    # This function triggers when someone type `<prefix>help <cog>`
    async def send_cog_help(self, cog):
        ctx = self.context

        # Do what you want to do here

    # This function triggers when someone type `<prefix>help <command>`
    async def send_command_help(self, command):
        ctx = self.context

        # Do what you want to do here

    # This function triggers when someone type `<prefix>help <group>`
    async def send_group_help(self, group):
        ctx = self.context

        # Do what you want to do here