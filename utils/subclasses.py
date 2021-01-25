"""
All the programmes subclasses live here.
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
import logging
import os
import re
import time
import asyncpg
import discord
import aiohttp

from contextlib import ContextDecorator, contextmanager
from discord.ext import commands
from datetime import datetime as dt
from . import utils
from .logger import create_logger


logger = create_logger("custom-bot", logging.INFO)


try:
    import uvloop  # type: ignore[reportMissingImports]
except ImportError:
    logger.warning("Using default asyncio event loop.")
    pass
else:
    logger.info("Using uvloop asyncio event loop.")
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


async def get_prefix(bot: commands.AutoShardedBot, message: discord.Message):
    """This gets called every message to get the prefix of the given message."""

    base = [f"<@{bot.user.id}> ", f"<@!{bot.user.id}> "]

    if message.guild is None:
        base.append("tb!")
        return base

    base.append(bot.config[message.guild.id]["guild_prefix"])

    if await bot.is_owner(message.author):
        if message.content.startswith(("jsk", "dev")):
            base.append("")

    return base


class CustomContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.timeit = TimeIt(self)
        self.bot: MyBot = self.bot

    @staticmethod
    def _owoify_message(content: str, embed: discord.Embed = None):
        ret = {"content": utils.owoify_text(content)}
        
        if embed:
            ret["embed"] = utils.owoify_embed(embed)

        return ret

    @contextmanager
    def embed(self, **kwargs):
        embed = self.bot.embed(self, **kwargs)
        yield embed

    async def send(self, content: str = None, **kwargs):
        kwargs["embed"] = kwargs.pop("embed", None)

        if self.guild and self.bot.config[self.guild.id]["owoify"]:
            owoified = self._owoify_message(content, kwargs["embed"])
            content = owoified["content"]

            if kwargs["embed"]:
                kwargs["embed"] = owofied["embed"]

        message = self.bot.ctx_cache.get(self.message.id, None)

        if message:
            return await message.edit(content=content, **kwargs)

        message = await super().send(content, **kwargs)

        if self.author.id in self.bot.owner_ids:
            self.bot.ctx_cache[self.message.id] = message

            async def cleanup():
                await asyncio.sleep(120)
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


class BaseCog(commands.Cog):
    def __init__(self, bot, show_name):
        super().__init__()
        self.bot = bot
        self.show_name = show_name


class MyBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(get_prefix, *args, **kwargs)

        # Prep for embed colour stuff. (Thank you to z03h for this :))
        c = dt.utcnow()
        hours, minutes, seconds = 0, 5, 0

        self.duration = (3600 * hours + 60 * minutes + seconds)
        self.embed_start_dt = dt(c.year, c.month, c.day)
        self.colours = [
            (210, 31, 255),
            (232, 132, 255),
            (216, 192, 255),
            (149, 182, 255),
            (93, 128, 255),
            (128, 84, 255),
            (169, 74, 255),
        ]
        self.per_colour = self.duration // len(self.colours)

        # Vars needed for some functionality.
        self.settings = utils.Settings("config.toml")
        self.maintenance_mode = self.settings["misc"]["maintenance_mode"]
        self.start_time = dt.now()
        self.support_url = "https://discord.gg/tKZbxAF"
        self.invite_url = "https://kal-byte.co.uk/invite/706530005169209386/2080763126"
        self.cmd_usage = 0
        self.announcement = {
            "title": None,
            "message": None
        }

        # Things for cache
        self.verification_config = {}
        self.giveaway_roles = {}
        self.blacklist = {}
        self.ctx_cache = {}
        self.config = {}

        # Stuff that requires the bots loop
        self.loop = asyncio.get_event_loop()
        self.pool = self.loop.run_until_complete(
            asyncpg.create_pool(
                **self.settings["database"]["main"] if os.name != "nt" else self.settings["database"]["beta"])
        )
        self.session = aiohttp.ClientSession(loop=self.loop)

        # Checks to disable functionality for certain things.
        self.add_check(self.command_check)
        self.add_check(self.blacklist_check)

        # Webhooks
        self.error_webhook = discord.Webhook.from_url(
            self.settings["misc"]["error_webhook"],
            adapter=discord.AsyncWebhookAdapter(self.session)
        )
        self.guild_webhook = discord.Webhook.from_url(
            self.settings["misc"]["guild_webhook"],
            adapter=discord.AsyncWebhookAdapter(self.session)
        )
        
        # Some tasks that prep the bot to be used fully.
        self.loop.create_task(self.do_prep())
        self.loop.create_task(self.chunk_all_guilds())

    @property
    def colour(self):
        c = dt.utcnow()
        td = c - self.embed_start_dt
        td = int(td.total_seconds() % self.duration)
        current_index, per = divmod(td, self.per_colour)
        per /= self.per_colour
        current_index = int(current_index % len(self.colours))
        next_index = int((current_index + 1) % len(self.colours))
        new_colour = [cc - int((cc - nc) * per) for cc, nc in zip(self.colours[current_index], self.colours[next_index])]
        return discord.Colour.from_rgb(*new_colour)

    async def close(self):
        await self.session.close()
        await self.pool.close()
        await super().close()

    async def chunk_all_guilds(self):
        await self.wait_until_ready()

        for guild in self.guilds:
            if guild.unavailable:
                continue

            await guild.chunk()

    async def do_prep(self):
        await self.wait_until_ready()

        # Credits to pikaninja for the refactor here down to just 1 query.
        for guild in self.guilds:
            sql = (
                "INSERT INTO guild_settings VALUES($1, DEFAULT, $2, $3, $4) "
                "ON CONFLICT (guild_id) DO NOTHING;"
            )
            values = (guild.id, None, None, False)
            await self.pool.execute(sql, *values)

        verification_config = await self.pool.fetch("SELECT message_id, role_id FROM guild_verification")
        guild_configs = await self.pool.fetch("SELECT * FROM guild_settings")
        blacklist = await self.pool.fetch("SELECT * FROM blacklist")
        giveaways = await self.pool.fetch("SELECT * FROM giveaways")

        for entry in verification_config:
            self.verification_config[entry["message_id"]] = entry["role_id"]

        logger.info("Finished caching the verification config")

        for entry in guild_configs:
            settings = dict(entry)
            settings.pop("guild_id")

            self.config[entry["guild_id"]] = settings

        logger.info("Finished caching guild configs")

        for entry in blacklist:
            self.blacklist[entry["id"]] = entry["reason"]

        logger.info("Finished caching blacklists")

        for entry in giveaways:
            if entry["role_id"]:
                self.giveaway_roles[entry["message_id"]] = entry["role_id"]

            await utils.set_giveaway(self, entry["ends_at"], entry["channel_id"], entry["message_id"])

        logger.info("Finished caching and setting giveaways")

        mutes = await self.pool.fetch("SELECT * FROM guild_mutes")
        for mute in mutes:
            now = time.time()
            seconds_left = mute["end_time"] - now
            await utils.set_mute(bot=self,
                                 guild_id=mute["guild_id"],
                                 user_id=mute["member_id"],
                                 _time=seconds_left)

        logger.info("Finished setting mutes.")

        updates_channel = self.get_channel(711586681580552232)
        last_update = await updates_channel.fetch_message(updates_channel.last_message_id)
        cool = last_update.content.split("\n")
        update = {
            "title": cool[0],
            "message": "\n".join(cool[1:])
        }

        self.announcement = update

        await self.change_presence(activity=discord.Game(name=self.settings["misc"]["status"]))

    @property
    def kal(self):
        return self.get_user(671777334906454026)
    

    def embed(self, ctx: CustomContext = None, **kwargs):
        kwargs["timestamp"] = dt.utcnow()
        kwargs["colour"] = kwargs.pop("colour", self.colour)
        embed = discord.Embed(**kwargs)

        if ctx:
            embed.set_footer(
                text=f"Requested by: {ctx.author}",
                icon_url=str(ctx.author.avatar_url)
            )
        else:
            embed.set_footer(text=f"Requested at")

        return embed

    async def get_context(self, message: discord.Message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    async def on_message(self, message: discord.Message):
        if not self.is_ready():
            return

        BOT_MENTION_REGEX = f"<@(!)?{self.user.id}>"

        if re.fullmatch(BOT_MENTION_REGEX, message.content):
            ctx = await self.get_context(message)
            cmd = self.get_command("prefix")

            await cmd(ctx)

        await self.process_commands(message)

    async def on_guild_join(self, guild: discord.Guild):
        await self.pool.execute(
            "INSERT INTO guild_settings(guild_id, guild_prefix, owoify) VALUES($1, $2, $3)",
            guild.id,
            "tb!",
            False,
        )

        self.config[guild.id] = {
            "guild_prefix": "tb!",
            "mute_role_id": None,
            "log_channel": None,
            "owoify": False,
        }

        message = [
            f"I was just added to {guild.name} with {guild.member_count} members.",
            f"Now in {len(self.guilds)} guilds.",
        ]

        logger.info("\n".join(message))

        await self.guild_webhook.send(content="\n".join(message),
                                      username="Added to guild.")

        await guild.chunk()

    async def on_guild_remove(self, guild: discord.Guild):
        await self.pool.execute(
            "DELETE FROM guild_settings WHERE guild_id = $1", guild.id
        )

        await self.pool.execute(
            "DELETE FROM guild_verification WHERE guild_id = $1", guild.id
        )

        del self.config[guild.id]

        message = [
            f"I was just removed from {guild.name} with {guild.member_count} members.",
            f"Now in {len(self.guilds)} guilds.",
        ]

        logger.info("\n".join(message))

        await self.guild_webhook.send(content="\n".join(message),
                                      username="Removed from guild.")

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.attachments and before.attachments:
            return

        if after.author.id in self.owner_ids:
            await self.process_commands(after)

    async def on_message_delete(self, message: discord.Message):
        try:
            cached_message = self.ctx_cache[message.id]
        except KeyError:
            return

        await cached_message.delete()

    async def command_check(self, ctx: CustomContext):
        if ctx.author.id in self.owner_ids:
            return True

        return not ctx.bot.maintenance_mode

    async def blacklist_check(self, ctx: CustomContext):
        try:
            reason = ctx.bot.blacklist[ctx.author.id]
        except KeyError:
            return True

        return False

    async def reply(self, message_id: int, content: str, **kwargs):
        message = self._connection._get_message(message_id)
        await message.reply(content, **kwargs)

    async def add_delete_reaction(self, channel_id: int, message_id: int):
        """Adds a reaction to delete the given message."""

        channel = self.get_channel(channel_id)

        if channel is None:
            return

        message = await channel.fetch_message(message_id)

        if message is None:
            return

        await message.add_reaction("\N{WASTEBASKET}")

        def _check(_reaction, _user):
            return _user != self.user and str(_reaction.emoji) == "\N{WASTEBASKET}"

        try:
            _, user = await self.wait_for(
                "reaction_add",
                timeout=10.0,
                check=_check
            )
        except asyncio.TimeoutError:
            pass
        else:
            try:
                await message.delete()
                await channel.send(f"Message was deleted by {user}")
            except (discord.Forbidden, discord.HTTPException):
                pass
