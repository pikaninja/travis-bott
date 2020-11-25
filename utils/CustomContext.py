import discord
from discord.ext import commands


class CustomContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def db(self):
        """Returns bot.pool"""

        return self.bot.pool

    async def thumbsup(self):
        """Adds a thumbs up emoji to a message"""

        try:
            return await self.message.add_reaction("\N{THUMBS UP SIGN}")
        except discord.HTTPException:
            pass
