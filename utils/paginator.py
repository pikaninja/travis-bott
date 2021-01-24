"""
Paginators to use within the program.
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

import discord
from discord.ext import commands, menus
from utils import utils
import asyncio

LAST_PAGE = "\N{LEFTWARDS BLACK ARROW}"
END_PAGE = "\N{CROSS MARK}"
NEXT_PAGE = "\N{BLACK RIGHTWARDS ARROW}"

PAGINATION_EMOJI = (LAST_PAGE, NEXT_PAGE, END_PAGE)


class CommandsPaginator(menus.ListPageSource):
    def __init__(self, data: commands.Paginator):
        super().__init__(data.pages, per_page=1)

    async def format_page(self, menu: menus.Menu, page):
        embed = menu.ctx.bot.embed(description=page)
        embed.set_footer(
            text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")

        return embed


class GeneralPageSource(menus.ListPageSource):
    def __init__(self, data: list, *, per_page: int):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu: menus.Menu, page: list):
        offset = menu.current_page * self.per_page
        embed = menu.ctx.bot.embed(menu.ctx)
        embed.description = "\n".join(
            [f"`{index + 1}`. {item}" for index, item in enumerate(page, offset)])

        return embed


class KalPages(menus.MenuPages):
    def __init__(self, source, **kwargs):
        super().__init__(source=source, check_embeds=True, **kwargs)

    async def finalize(self, timed_out):
        try:
            if timed_out:
                await self.message.clear_reactions()
            else:
                await self.message.delete()
        except discord.HTTPException:
            pass

    @menus.button("\N{PUBLIC ADDRESS LOUDSPEAKER}", position=menus.Last(6))
    async def announcements(self, payload):
        """Announcements go here"""

        embed = self.bot.embed(self.ctx)
        embed.title = self.bot.announcement["title"]
        embed.description = self.bot.announcement["message"]

        await self.message.edit(content=None, embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())


class MainHelp(menus.ListPageSource):
    def __init__(self, ctx, categories: list, *, prefix):
        super().__init__(entries=categories, per_page=4)
        self.ctx = ctx
        self.prefix = prefix

    async def format_page(self, menu, category):
        embed = self.ctx.bot.embed(
            title="Bot Help",
            description=(
                f"{self.ctx.bot.description}\n"
                + "`<arg> | Required`\n"
                + "`[arg] | Optional`\n"
                + "`<|[arg...]|> Takes multiple arguments, follows the same rules as above.`\n"
            )
        )
        embed.set_footer(
            text=f"Do \"{self.prefix}help [command|category]\" for more info on a command.")

        for k, v in category:
            embed.add_field(name=k, value=v, inline=False)

        return embed


class GroupHelp(menus.ListPageSource):
    def __init__(self, ctx, group, cmds, *, prefix):
        super().__init__(entries=cmds, per_page=4)
        self.ctx = ctx
        self.group = group
        self.prefix = prefix

    async def format_page(self, menu, cmds):
        embed = self.ctx.bot.embed()
        embed.title = f"{self.prefix}{self.group.qualified_name} {self.group.signature}"
        embed.description = self.group.help.format(prefix=self.ctx.prefix)

        for cmd in cmds:
            signature = f"{self.prefix}{cmd.qualified_name} {cmd.signature}"
            embed.add_field(
                name=signature, value=cmd.help.format(prefix=self.ctx.prefix) or "No help given...", inline=False)

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
        embed = self.ctx.bot.embed()
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


class EmbedMenu(menus.ListPageSource):
    def __init__(self, embeds, per_page=1):
        super().__init__(embeds, per_page=per_page)

    async def format_page(self, menu, page):
        page.set_footer(
            text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return page


class Menu(menus.Menu):
    def __init__(self, pages, embed: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.pages = pages
        self.embed = embed
        self.cur_page = 0

    async def change(self):
        new_page = self.pages[self.cur_page]
        if self.embed:
            await self.message.edit(embed=new_page)
        else:
            await self.message.edit(content=new_page)

    async def send_initial_message(self, ctx, channel):
        if self.embed:
            return await channel.send(embed=self.pages[self.cur_page])
        else:
            return await channel.send(content=self.pages[self.cur_page])

    @menus.button("\N{LEFTWARDS BLACK ARROW}")
    async def previous_page(self, payload):
        if self.cur_page > 0:
            self.cur_page -= 1
            await self.change()

    @menus.button("\N{BLACK SQUARE FOR STOP}")
    async def stop_pages(self, payload):
        self.stop()

    @menus.button("\N{BLACK RIGHTWARDS ARROW}")
    async def next_page(self, payload):
        if self.cur_page < len(self.pages) - 1:
            self.cur_page += 1
            await self.change()


class BetterPaginator:
    def __init__(
        self,
        ctx: commands.Context,
        entries: list,
        embed: bool = True,
        timeout: int = 300.0
    ) -> None:
        self.ctx = ctx
        self.entries = entries
        self.embed = embed
        self.timeout = timeout

        self.channel = ctx.channel
        self.msg = ctx.message
        self.max_pages = len(entries) - 1
        self.paginating = True
        self.page = 0
        self.reactions = [
            ("\N{LEFTWARDS BLACK ARROW}", self.backward),
            ("\N{BLACK RIGHTWARDS ARROW}", self.forward),
            ("\N{CROSS MARK}", self.stop),
            ("\N{INFORMATION SOURCE}", self.info)
        ]

    async def setup(self):
        if not self.embed:
            try:
                self.msg = await self.channel.send(self.entries[0])
            except AttributeError:
                await self.channel.send(self.entries)
        else:
            try:
                self.msg = await self.channel.send(embed=self.entries[0])
            except (AttributeError, TypeError):
                await self.channel.send(embed=self.entries)

        if len(self.entries) == 1:
            return

        for (r, _) in self.reactions:
            await self.msg.add_reaction(r)

    async def alter(self, page: int):
        try:
            await self.msg.edit(content=None, embed=self.entries[page])
        except (AttributeError, TypeError):
            await self.msg.edit(content=self.entries[page], embed=None)

    async def backward(self):
        if self.page == 0:
            self.page = self.max_pages
            await self.alter(self.page)
        else:
            self.page -= 1
            await self.alter(self.page)

    async def forward(self):
        if self.page == self.max_pages:
            self.page = 0
            await self.alter(self.page)
        else:
            self.page += 1
            await self.alter(self.page)

    async def stop(self):
        msg = await self.msg.channel.fetch_message(self.msg.id)

        for reaction in msg.reactions:
            if reaction.me:
                await reaction.remove(self.ctx.bot.user)

        self.paginating = False

    async def info(self):
        embed = self.ctx.bot.embed(self.ctx)
        embed.description = (
            f"{self.ctx.bot.description}\n"
            + "`<arg> | Required`\n"
            + "`[arg] | Optional`\n"
            + "`<|[arg...]|> Takes multiple arguments, follows the same rules as above.`\n"
        )

        await self.msg.edit(embed=embed)

    def _check(self, reaction, user):
        if user.id != self.ctx.author.id:
            return False

        if reaction.message.id != self.msg.id:
            return False

        for (emoji, func) in self.reactions:
            if reaction.emoji == emoji:
                self.execute = func
                return True
        return False

    async def paginate(self):
        await self.setup()
        while self.paginating:
            done, pending = await asyncio.wait(
                [self.ctx.bot.wait_for("reaction_add", check=self._check, timeout=self.timeout),
                 self.ctx.bot.wait_for("reaction_remove", check=self._check, timeout=self.timeout)],
                return_when=asyncio.FIRST_COMPLETED)
            try:
                done.pop().result()
            except asyncio.TimeoutError:
                return self.stop

            for future in pending:
                future.cancel()
            await self.execute()


class AutoReactMenu:
    async def paginate(self, ctx) -> discord.Message:
        def event_check(reaction: discord.Reaction, member: discord.Member):
            return all(
                (
                    member == ctx.author,
                    reaction.message.id == msg.id,
                    member.id != ctx.bot.user.id,
                )
            )

        embed = utils.embed_message(
            title="Auto-React Setup",
            message="Welcome to the setup for auto-reactions.\n"
            "Please confirm whether you'd like to continue or not.",
        )

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{CROSS MARK}")

        try:
            reaction, member = await ctx.bot.wait_for(
                "reaction_add", timeout=10.0, check=event_check
            )
        except asyncio.TimeoutError:
            await msg.delete()
            return
        else:
            if str(reaction.emoji) == "\N{WHITE HEAVY CHECK MARK}":
                await msg.remove_reaction(reaction.emoji, ctx.author)
                embed.title = "Are you adding or removing an Auto-Reaction?"
                embed.description = (
                    "\N{WHITE HEAVY CHECK MARK} Add\n" "\N{CROSS MARK} Remove"
                )

                await msg.edit(embed=embed)

                try:
                    reaction, member = await ctx.bot.wait_for(
                        "reaction_add", timeout=10.0, check=event_check
                    )
                except asyncio.TimeoutError:
                    return
                else:
                    if str(reaction.emoji) == "\N{WHITE HEAVY CHECK MARK}":
                        # TODO: Query user to provide a channel and what emoji to add.
                        # Then add that to the DB
                        return

                    if str(reaction.emoji) == "\N{CROSS MARK}":
                        # TODO: Query user to provide a channel and what emoji to remove
                        # Then query DB to see if that exists and remove it if so else tell user if not.
                        return

            if str(reaction.emoji) == "\N{CROSS MARK}":
                await msg.delete()
                return


class Paginator:
    def __init__(
        self,
        embeds: list,
        emojis: list = None,
        delete_after: bool = False,
        timeout: int = 60.0,
        clear_reactions: bool = False,
    ) -> None:
        self.embeds = embeds
        self.emojis = emojis
        self.delete_after = delete_after
        self.timeout = timeout
        self.clear_reactions = clear_reactions
        self.page = 0

        if self.delete_after == True and self.timeout <= 0:
            raise Exception(
                "You told me to delete the message after but provided no timeout."
            )

    async def paginate(self, ctx) -> discord.Message:
        def event_check(reaction: discord.Reaction, member: discord.Member):
            return all(
                (
                    member == ctx.author,
                    reaction.message.id == message.id,
                    str(reaction.emoji) in PAGINATION_EMOJI,
                    member.id != ctx.bot.user.id,
                )
            )

        message = await ctx.send(embed=self.embeds[self.page])

        for emoji in PAGINATION_EMOJI:
            await message.add_reaction(emoji)

        if self.emojis is not None:
            for emoji in self.emojis:
                await message.add_reaction(emoji)

        while True:
            try:
                reaction, member = await ctx.bot.wait_for(
                    "reaction_add",
                    timeout=self.timeout if self.timeout > 0 else None,
                    check=event_check,
                )
            except asyncio.TimeoutError:
                if self.clear_reactions:
                    try:
                        await message.clear_reactions()
                    except discord.Forbidden:
                        pass

                if self.delete_after:
                    await message.delete()

                break

            else:

                if str(reaction.emoji) == END_PAGE:
                    self.page = 0

                    if self.delete_after:
                        return await message.delete()
                    else:
                        try:
                            await message.clear_reactions()
                        except discord.Forbidden:
                            break

                if str(reaction.emoji) == NEXT_PAGE:
                    try:
                        await message.remove_reaction(reaction.emoji, member)
                    except discord.Forbidden:
                        pass

                    if len(self.embeds) == self.page + 1:
                        continue

                    self.page += 1

                    await message.edit(embed=self.embeds[self.page])

                if str(reaction.emoji) == LAST_PAGE:
                    try:
                        await message.remove_reaction(reaction.emoji, member)
                    except discord.Forbidden:
                        pass

                    if self.page == 0:
                        continue

                    self.page -= 1

                    await message.edit(embed=self.embeds[self.page])
