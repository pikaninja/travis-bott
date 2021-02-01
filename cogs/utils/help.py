"""
Initializes the help command.
Copyright (C) 2021 kal-byte

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from typing import List, Mapping
import discord
import utils
from discord.ext import commands, menus


class GroupHelp(menus.ListPageSource):
    def __init__(self, group, cmds, *, prefix):
        super().__init__(entries=cmds, per_page=4)
        self.group = group
        self.prefix = prefix

    async def format_page(self, menu, cmds):
        embed = menu.ctx.bot.embed(menu.ctx)
        command_name = f"{self.group.qualified_name}{' | ' + ' | '.join(self.group.aliases) if self.group.aliases else ''}"
        embed.title = f"{self.prefix}{command_name} {self.group.signature}"
        embed.description = (
            self.group.help.format(prefix=self.prefix) +
            f"\n\n**Category: {self.group.cog.show_name}**"
        )

        for cmd in cmds:
            command_name = f"{cmd.qualified_name}{' | ' + ' | '.join(cmd.aliases) if cmd.aliases else ''}"
            signature = f"{self.prefix}{command_name} {cmd.signature}"
            embed.add_field(
                name=signature, value=cmd.help.format(prefix=self.prefix) or "No help given...", inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(
                name=f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)")

        embed.set_footer(
            text=f"Do \"{self.prefix}help [command|category]\" for more info on a command.")
        return embed


class CogHelp(menus.ListPageSource):
    def __init__(self, ctx, cog, cmds, *, prefix):
        super().__init__(entries=cmds, per_page=4)
        self.ctx = ctx
        self.cog = cog
        self.prefix = prefix
        self.title = f"{self.cog.show_name} Commands"

    async def format_page(self, menu, cmds):
        embed = self.ctx.bot.embed(menu.ctx)
        embed.title = self.title

        for cmd in cmds:
            signature = f"{self.prefix}{cmd.name} {cmd.signature}"
            embed.add_field(
                name=signature,
                value=cmd.help.format(prefix=self.prefix),
                inline=False
            )

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(
                name=f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)")

        embed.set_footer(
            text=f"Do \"{self.prefix}help [command|category]\" for more info on a command.")
        return embed


class BaseHelp(menus.Menu):
    def __init__(self, data, prefix, **kwargs):
        kwargs["delete_message_after"] = True
        super().__init__(**kwargs)

        self.data = data
        self.prefix = prefix
        self.message = None

    async def _prepare_menu_for(self, what_cog):
        await self.message.delete()
        self.message = None
        cog = self.bot.get_cog(what_cog)
        menu = utils.KalPages(
            CogHelp(self.ctx, cog, cog.get_commands(), prefix=self.prefix),
            clear_reactions_after=True
        )
        return menu

    async def send_initial_message(self, ctx: utils.CustomContext, channel: discord.TextChannel):
        embed = self.bot.embed(ctx)
        embed.description = (
            "```fix\n"
            f"{self.bot.description}\n"
            "<> → Means the argument is required\n"
            "[] → Means the argument is optional\n"
            f"Make sure to join the bots support server if you need help. ({self.prefix}support)```"
        )
        modules = []

        for title in self.data:
            modules.append(f"{title}")

        embed.add_field(
            name="Modules",
            value="\n".join(modules)
        )

        embed.add_field(
            name="News",
            value=self.bot.announcement["title"] + "\n" +
            self.bot.announcement["message"].format(prefix=self.prefix)
        )

        self.message = await channel.send(embed=embed)

        await self.message.add_reaction("\N{CROSS MARK}")

        return self.message

    @menus.button("\N{ROBOT FACE}")
    async def meta_help(self, payload):
        menu = await self._prepare_menu_for("meta")
        await menu.start(self.ctx)

    @menus.button("\N{SHIELD}")
    async def mgmt_help(self, payload):
        menu = await self._prepare_menu_for("management")
        await menu.start(self.ctx)

    @menus.button("\N{CROSSED SWORDS}")
    async def mod_help(self, payload):
        menu = await self._prepare_menu_for("moderation")
        await menu.start(self.ctx)

    @menus.button("\N{PARTY POPPER}")
    async def fun_help(self, payload):
        menu = await self._prepare_menu_for("fun")
        await menu.start(self.ctx)

    @menus.button("\N{EYE}")
    async def img_help(self, payload):
        menu = await self._prepare_menu_for("imagemanipulation")
        await menu.start(self.ctx)

    @menus.button("\N{DIZZY SYMBOL}")
    async def misc_help(self, payload):
        menu = await self._prepare_menu_for("misc")
        await menu.start(self.ctx)

    @menus.button("\N{CROSS MARK}")
    async def stop_pages(self, payload):
        self.stop()
        await self.message.delete()
        self.message = None


class CustomHelp(commands.HelpCommand):
    def __init__(self, **options):
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

    def command_not_found(self, string):
        string = string[:15] + "..." if len(string) > 15 else string
        return f"Couldn't find the help for `{string}`"

    async def send_bot_help(self, mapping: Mapping[commands.Cog, List[commands.Command]]):
        titles = []
        for cog, all_commands in mapping.items():
            if not hasattr(cog, "show_name"):
                continue
            if sum(not c.hidden for c in all_commands) == 0:
                continue

            titles.append(cog.show_name)

        menu = BaseHelp(titles, self.clean_prefix)
        await menu.start(self.context)

    async def send_command_help(self, command: commands.Command):
        if not hasattr(command.cog, "show_name"):
            return await self.send_error_message(self.command_not_found(command.qualified_name))

        embed = self.context.bot.embed(self.context)
        command_name = f"{command.qualified_name}{' | ' + ' | '.join(command.aliases) if command.aliases else ''}"
        embed.title = f"{self.clean_prefix}{command_name} {command.signature}"
        embed.description = (
            command.help +
            f"\n\n**Category: {command.cog.show_name}**"
        )

        await self.context.send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        if not hasattr(group.cog, "show_name"):
            return await self.send_error_message(self.command_not_found(group.qualified_name))

        sorted = await self.filter_commands(group.commands, sort=True)
        menu = utils.KalPages(
            GroupHelp(group, sorted, prefix=self.clean_prefix))
        await menu.start(self.context)


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
