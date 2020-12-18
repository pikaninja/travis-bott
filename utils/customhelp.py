from discord.ext import commands
from utils.embed import Embed
from utils import CustomContext
from utils.customcog import BaseCog
from utils.paginator import GroupHelp, KalPages, MainHelp, CogHelp


class CustomHelp(commands.HelpCommand):
    def __init__(self, context=CustomContext, **options):
        super().__init__(**options)

    async def filter_commands(self, commands, *, sort=False, key=None):
        """Custom version of filter commands due to me not liking the way it filters out cmds that are permission based."""

        if sort and key is None:
            def key(c): return c.name

        iterator = filter(lambda c: not c.hidden, commands)

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

    def get_command_signature(self, command: commands.Command):
        return f"{self.clean_prefix}{command.qualified_name} {command.signature}"

    async def command_not_found(self, string):
        """My own impl of the command not found error."""

        if len(string) >= 50:
            return f"Could not find the command `{string[:20]}...`"
        else:
            return f"Could not find the command `{string}`"

    async def send_bot_help(self, mapping):
        cats = []
        for cog, commands in mapping.items():
            if not hasattr(cog, "show_name"):
                continue
            name = "No Category" if cog is None else cog.show_name
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                all_cmds = " • ".join(f"`{c.name}`" for c in commands)
                if cog and cog.description:
                    cats.append([name, f">>> {all_cmds}\n"])

        menu = KalPages(source=MainHelp(self.context, cats, prefix=self.clean_prefix))
        await menu.start(self.context)

    async def send_cog_help(self, cog: BaseCog):
        if not hasattr(cog, "show_name"):
            pass

        entries = await self.filter_commands(cog.get_commands(), sort=True)
        menu = KalPages(
            CogHelp(self.context, cog, entries, prefix=self.clean_prefix),
            clear_reactions_after=True
        )
        await menu.start(self.context)

    async def send_group_help(self, group: commands.Group):
        if not hasattr(group.cog, "show_name"):
            pass

        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = GroupHelp(self.context, group, entries,
                           prefix=self.clean_prefix)
        menu = KalPages(source, clear_reactions_after=True)
        await menu.start(self.context)

    async def send_command_help(self, command: commands.Command):
        if not hasattr(command.cog, "show_name"):
            pass

        embed = Embed.default(self.context)
        embed.title = self.get_command_signature(command)
        embed.set_footer(
            text=f"Do \"{self.clean_prefix}help [command|category]\" for more info on a command.")

        if command.description:
            embed.description = (
                f"{command.description.format(prefix=self.clean_prefix)}\n\n"
                f"{command.help.format(prefix=self.clean_prefix)}"
            )

        else:
            embed.description = command.help.format(
                prefix=self.clean_prefix) or "No help found..."
        await self.get_destination().send(embed=embed)
