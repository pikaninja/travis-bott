import time
from contextlib import ContextDecorator

import discord
from discord.ext import commands


class CommandConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return ctx.bot.get_command(argument)


class CustomContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.timeit = timeit(self)

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


class timeit(ContextDecorator):
    def __init__(self, ctx):
        self.ctx = ctx

    async def __aenter__(self):
        self.start = time.perf_counter()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end = time.perf_counter()

        await self.ctx.send(f"Finished in `{self.end - self.start:,.2f}` seconds")
