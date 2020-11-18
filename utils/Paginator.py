import typing
import discord
from discord import embeds
from discord.ext import commands
from utils import utils
from utils.Embed import Embed
import asyncio

LAST_PAGE = "\N{LEFTWARDS BLACK ARROW}"
END_PAGE = "\N{CROSS MARK}"
NEXT_PAGE = "\N{BLACK RIGHTWARDS ARROW}"

PAGINATION_EMOJI = (LAST_PAGE, NEXT_PAGE, END_PAGE)


class BetterPaginator:
    def __init__(
        self,
        ctx: commands.Context,
        entries: list,
        embed: bool = True,
        timeout: int = 300.0,
        delete_after: bool = False
    ) -> None:
        self.ctx = ctx
        self.entries = entries
        self.embed = embed
        self.timeout = timeout
        self.delete_after = delete_after
        
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
        if self.embed == False:
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
        try:
            await self.msg.clear_reactions()
        except discord.Forbidden:
            if self.delete_after:
                await self.msg.delete()
            else:
                pass
        
        self.paginating = False
    
    async def info(self):
        embed = Embed.default(self.ctx)
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
