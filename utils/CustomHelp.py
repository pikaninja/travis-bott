from discord.ext import commands, menus

from utils import utils
from utils.Embed import Embed
from utils import CustomContext
from utils.CustomCog import BaseCog
from utils.Paginator import GroupHelp, KalPages

import Levenshtein


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

    def get_ending_note(self):
        return f"Use {self.clean_prefix}{self.invoked_with} [category|command] for more info on a command."

    def get_command_signature(self, command: commands.Command):
        return f"{self.clean_prefix}{command.qualified_name} {command.signature}"

    async def command_not_found(self, string):
        """My own impl of the command not found error."""

        if len(string) >= 50:
            difference = utils.get_best_difference([c.name for c in self.context.bot.commands], string)
            if difference:
                return f"Could not find the command `{string[:20]}...` did you mean `{difference}`?."
            return f"Could not find the command `{string[:20]}...`"
        else:
            difference = utils.get_best_difference([c.name for c in self.context.bot.commands], string)
            if difference:
                return f"Could not find the command `{string}` did you mean `{difference}`?."
            return f"Could not find the command `{string}`"

    async def send_bot_help(self, mapping):
        embed = Embed.default(self.context, title="Bot Commands")
        embed.description = (
            f"{self.context.bot.description}\n"
            + "`<arg> | Required`\n"
            + "`[arg] | Optional`\n"
            + "`<|[arg...]|> Takes multiple arguments, follows the same rules as above.`\n"
        )

        for cog, commands in mapping.items():
            if not hasattr(cog, "show_name"):
                continue
            name = "No Category" if cog is None else cog.show_name
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                all_cmds = " • ".join(f"`{c.name}`" for c in commands)
                if cog and cog.description:
                    embed.add_field(
                        name=name, value=f">>> {all_cmds}\n", inline=False)
                # value = " ".join("`" + c.name + "`" for c in commands)
                # if cog and cog.description:
                #     value = f"{cog.description}\n{value}"

                # embed.add_field(name=name, value=value)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: BaseCog):
        if not hasattr(cog, "show_name"):
            pass

        entries = await self.filter_commands(cog.get_commands(), sort=True)
        menu = KalPages(
            GroupHelp(self.context, cog, entries, prefix=self.clean_prefix),
            clear_reactions_after=True
        )
        await menu.start(self.context)

        # embed = Embed.default(self.context, title=f"{cog.show_name} Commands")
        #
        # filtered = await self.filter_commands(cog.get_commands(), sort=True)
        #
        # for command in filtered:
        #     embed.add_field(
        #         name=f"{command.qualified_name}",
        #         value=f"{command.help.format(prefix=self.clean_prefix)}",
        #         inline=False
        #     )
        #
        # embed.set_footer(text=self.get_ending_note())
        # await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group):
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

        # embed = Embed.default(
        #     self.context,
        #     title=f"{self.clean_prefix}{group.qualified_name} {group.signature}"
        # )
        # if group.help:
        #     aliases = (
        #         f"*Aliases: {' | '.join('`' + x + '`' for x in  group.aliases)}*"
        #         if group.aliases
        #         else ""
        #     )
        #     group_cat = group.cog.qualified_name
        #     embed.description = (
        #         str(group.help).format(prefix=self.clean_prefix)
        #         + "\n"
        #         + aliases
        #         + "\n"
        #         + f"Category: {group_cat}"
        #     )
        #
        # if isinstance(group, commands.Group):
        #     filtered = await self.filter_commands(group.commands, sort=True)
        #     for command in filtered:
        #         embed.add_field(
        #             name=self.get_command_signature(command),
        #             value=str(command.short_doc) or "...",
        #             inline=False,
        #         )
        #
        # embed.set_footer(text=self.get_ending_note())
        # await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = Embed.default(self.context)
        embed.title = self.get_command_signature(command)
        if command.description:
            embed.description = f"{command.description}\n\n{command.help}"
        else:
            embed.description = command.help or "No help found..."
        await self.get_destination().send(embed=embed)

    # This doesnt appear to work...
    # yes I've even tried without my error handler, same result.

    # async def send_error_message(self, error):
    #     await self.get_destination().send(error)
