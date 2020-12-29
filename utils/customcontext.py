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

        self.timeit = TimeIt(self)

    async def _owoify(self, method, *args, **kwargs):
        if embed := kwargs.get("embed", None):
            embed = utils.owoify_embed(embed)
            kwargs["embed"] = embed

        text = utils.owoify_text(str(*args))
        message = await method(content=text, **kwargs)

        if self.author.id in self.bot.owner_ids:
            if not getattr(message, "edited_at", None):
                self.bot.ctx_cache[self.message.id] = message

        return message

    async def send(self, *args, **kwargs):
        try:
            if self.message.attachments or kwargs.get("file") or kwargs.get("files") or kwargs.get("new_message"):
                raise KeyError

            message = self.bot.ctx_cache[self.message.id]

            if self.guild:
                if self.bot.config[self.guild.id]["owoify"]:
                    return await self._owoify(message.edit, *args, **kwargs)

            await message.edit(content=str(*args), **kwargs)
            return message
        except KeyError:
            if kwargs.get("new_message"):
                kwargs.pop("new_message")

            if self.guild:
                if self.bot.config[self.guild.id]["owoify"]:
                    return await self._owoify(super().send, *args, **kwargs)

            message = await super().send(*args, **kwargs)

            if self.author.id in self.bot.owner_ids:
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


class TimeIt(ContextDecorator):
    def __init__(self, ctx):
        self.ctx = ctx

    async def __aenter__(self):
        self.start = time.perf_counter()

    async def __aexit__(self, *args):
        self.end = time.perf_counter()

        await self.ctx.send(f"Finished in `{self.end - self.start:,.2f}` seconds",
                            new_message=True)
