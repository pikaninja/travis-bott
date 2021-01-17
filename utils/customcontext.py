"""
Context Subclass to provide extra usability.
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

import asyncio
import contextlib
import time
import utils
import discord
from contextlib import ContextDecorator, asynccontextmanager, contextmanager, suppress
from discord.ext import commands
from utils.embed import Embed


class CommandConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return ctx.bot.get_command(argument)


class CustomContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.timeit = TimeIt(self)

    async def _owoify(self, method, *args, **kwargs):
        if embed := kwargs.pop("embed", None):
            embed = utils.owoify_embed(embed)
            kwargs["embed"] = embed

        text = utils.owoify_text(str(*args))
        message = await method(content=text, **kwargs)

        if await self.bot.is_owner(self.author):
            if not getattr(message, "edited_at", None):
                self.bot.ctx_cache[self.message.id] = message

        return message

    @contextmanager
    def embed(self, **kwargs):
        embed = Embed.default(self, **kwargs)
        yield embed

    async def send(self, *args, **kwargs):
        try:
            if self.message.attachments or kwargs.get("file") or kwargs.get("files") or kwargs.get("new_message"):
                raise KeyError

            kwargs["embed"] = kwargs.pop("embed", None)

            message = self.bot.ctx_cache[self.message.id]

            if self.guild:
                if self.bot.config[self.guild.id]["owoify"]:
                    return await self._owoify(message.edit, *args, **kwargs)

            await message.edit(content=str(*args), **kwargs)
            return message
        except KeyError:
            kwargs.pop("new_message", None)

            if self.guild:
                if self.bot.config[self.guild.id]["owoify"]:
                    return await self._owoify(super().send, *args, **kwargs)

            message = await super().send(*args, **kwargs)

            if await self.bot.is_owner(self.author):
                self.bot.ctx_cache[self.message.id] = message

                async def cleanup():
                    await asyncio.sleep(300)
                    with contextlib.suppress(KeyError):
                        del self.bot.ctx_cache[self.message.id]

                self.bot.loop.create_task(cleanup())

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
