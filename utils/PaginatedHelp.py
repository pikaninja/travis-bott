import discord
from discord.ext import commands, menus

from utils.Paginator import Paginator
from utils import utils


class BotHelpPage(menus.ListPageSource):
    def __init__(self, help_cmd, commands):
        super().__init__(
            entries=sorted(commands.keys(), key=lambda c: c.qualified_name), per_page=6
        )
        self.commands = commands
        self.help_cmd = help_cmd
        self.prefix = help_cmd.clean_prefix

    def format_commands(self, cog, commands):
        if cog.description:
            short_doc = cog.description.split("\n", 1)[0] + "\n"
        else:
            short_doc = "No help found...\n"

        current_count = len(short_doc)
        ending_note = "+%d not shown."
        ending_length = len(ending_note)

        page = []
        for command in commands:
            value = f"`{command.name}`"
            count = len(value) + 1
            if count + current_count < 700:
                current_count += count
                page.append(value)
            else:
                if current_count + ending_length + 1 > 800:
                    page.pop()
                break

        if len(page) == len(commands):
            return short_doc + " ".join(page)

        hidden = len(commands) - len(page)
        return short_doc + " ".join(page) + "\n" + (ending_note % hidden)

    async def format_page(self, menu, cogs):
        prefix = menu.ctx.prefix
        description = (
            f"{menu.ctx.bot.description}\n"
            "`<arg> | Required`\n"
            "`[arg] | Optional`\n"
            "`<|[arg...]|> | Takes multiple arguments, same rules above apply.`"
        )

        embed = utils.embed_message(title="Categories", message=description)

        for cog in cogs:
            commands = self.commands.get(cog)
            if commands:
                value = self.format_commands(cog, commands)
            embed.add_field(name=cog.qualified_name, value=value, inline=True)

        maximum = self.get_max_pages()
        embed.set_footer(text=f"Page {menu.current_page + 1}/{maximum}")
        return embed


class HelpMenu(menus.MenuPages):
    def __init__(self, source):
        super().__init__(source=source, check_embeds=True)

    async def finalize(self, timed_out):
        try:
            if timed_out:
                await self.message.clear_reactions()
            else:
                await self.message.delete()
        except discord.HTTPException:
            pass


class HelpCommand(commands.HelpCommand):
    async def filter_commands(self, commands, *, sort=False, key=None):
        """Custom version of filter commands due to me not liking the way it filters out cmds that are permission based."""

        if sort and key is None:
            key = lambda c: c.name

        iterator = (
            commands if self.show_hidden else filter(lambda c: not c.hidden, commands)
        )

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

        entries = await self.filter_commands(ctx.bot.commands)

        all_commands = {}
        for command in entries:
            if command.cog is None:
                continue
            try:
                all_commands[command.cog].append(command)
            except KeyError:
                all_commands[command.cog] = [command]

        menu = HelpMenu(BotHelpPage(self, all_commands))
        await menu.start(ctx)

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
