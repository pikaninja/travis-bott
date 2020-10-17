import typing
import discord
from discord import embeds
from discord.ext import commands
from utils import utils
import asyncio

LAST_PAGE = "\N{LEFTWARDS BLACK ARROW}"
END_PAGE = "\N{CROSS MARK}"
NEXT_PAGE = "\N{BLACK RIGHTWARDS ARROW}"

PAGINATION_EMOJI = (LAST_PAGE, NEXT_PAGE, END_PAGE)

class Paginator():
    def __init__(self, embeds: typing.List) -> None:
        self.embeds = embeds
        self.page = 0

    async def paginate(self, ctx, timeout: int = 60) -> discord.Message:
        def event_check(reaction: discord.Reaction, member: discord.Member):
            return all((
                    member == ctx.author,
                    reaction.message.id == message.id,
                    str(reaction.emoji) in PAGINATION_EMOJI,
                    member.id != ctx.bot.user.id
                ))

        message = await ctx.send(embed=self.embeds[self.page])

        for emoji in PAGINATION_EMOJI:
            await message.add_reaction(emoji)
        
        while True:
            try:
                reaction, member = await ctx.bot.wait_for("reaction_add", timeout=timeout, check=event_check)
            except asyncio.TimeoutError:
                break

            else:
                
                if str(reaction.emoji) == END_PAGE:
                    self.page = 0
                    return await message.delete()
                
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