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
    def __init__(
        self,
        embeds: list,
        emojis: list = None,
        delete_after: bool = False,
        timeout: int = 60.0,
        clear_reactions: bool = False
    ) -> None:
        self.embeds = embeds
        self.emojis = emojis
        self.delete_after = delete_after
        self.timeout = timeout
        self.clear_reactions = clear_reactions
        self.page = 0

        if self.delete_after == True and self.timeout <= 0:
            raise Exception("You told me to delete the message after but provided no timeout.")

    async def paginate(self, ctx) -> discord.Message:
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

        if self.emojis is not None:
            for emoji in self.emojis:
                await message.add_reaction(emoji)
        
        while True:
            try:
                reaction, member = await ctx.bot.wait_for("reaction_add", timeout=self.timeout if self.timeout > 0 else None, check=event_check)
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