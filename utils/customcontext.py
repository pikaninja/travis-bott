import random
import time
from contextlib import ContextDecorator

import discord
from discord.ext import commands

import utils


class CommandConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return ctx.bot.get_command(argument)



class CustomContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.timeit = timeit(self)

    async def _owoify(self, method, *args, **kwargs):
        if embed := kwargs.get("embed", None):
            embed = utils.owoify_embed(embed)
            kwargs["embed"] = embed

        text = utils.owoify_text(str(*args))
        message = await method(text, **kwargs)
        self.bot.ctx_cache[self.message.id] = message
        return message

    async def send(self, *args, **kwargs):
        try:
            if self.message.attachments or kwargs.get("file") or kwargs.get("files") or kwargs.get("new_message"):
                raise KeyError

            message = self.bot.ctx_cache[self.message.id]

            if self.guild.id == 336642139381301249:
                return await self._owoify(message.edit, *args, **kwargs)

            await message.edit(content=str(*args), **kwargs)
            return message
        except KeyError:
            if kwargs.get("new_message"):
                kwargs.pop("new_message")

            if self.guild.id == 336642139381301249:
                return await self._owoify(super().send, *args, **kwargs)

            message = await super().send(*args, **kwargs)
            self.bot.ctx_cache[self.message.id] = message
            return message

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

        await self.ctx.send(f"Finished in `{self.end - self.start:,.2f}` seconds",
                            new_message=True)
