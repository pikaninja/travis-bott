import time
from contextlib import asynccontextmanager

import discord
from discord.ext import commands


class CommandConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return ctx.bot.get_command(argument)


class CustomContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def db(self):
        """Returns bot.pool"""

        return self.bot.pool

    @asynccontextmanager
    async def timeit(self, command: commands.Command, *args, **kwargs):
        """Times how long it takes to finish a command."""

        command = self.bot.get_command(command)
        start = time.perf_counter()
        await self.invoke(command, *args, **kwargs)
        end = time.perf_counter()
        yield end - start

    async def thumbsup(self):
        """Adds a thumbs up emoji to a message"""

        try:
            return await self.message.add_reaction("\N{THUMBS UP SIGN}")
        except discord.HTTPException:
            pass
