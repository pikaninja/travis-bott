"""
Bot Subclass for more fine tuning within the bot itself.
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
import logging
import os
import re
import time
import asyncpg
import discord
import aiohttp
import toml

from discord.ext import commands
from datetime import datetime as dt

from .logger import create_logger
from .customcontext import CustomContext
from .utils import set_mute, set_giveaway


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


class MyBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(get_prefix, *args, **kwargs)

        self.start_time = dt.now()

        self.config = {}
        self.verification_config = {}
        self.giveaway_roles = {}

        self.loop = asyncio.get_event_loop()
        self.pool = self.loop.run_until_complete(
            asyncpg.create_pool(**self.database_for("main")
                                if os.name != "nt" else self.database_for("beta"))
        )

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.loop.create_task(self.do_prep())
        self.announcement = {
            "title": None,
            "message": None
        }
        self.maintenance_mode = False
        self.add_check(self.command_check)
        self.add_check(self.blacklist_check)

        self.support_url = "https://discord.gg/tKZbxAF"
        self.invite_url = "https://kal-byte.co.uk/invite/706530005169209386/2080763126"

        self.blacklist = {}
        self.error_webhook = discord.Webhook.from_url(
            self.from_config("error_webhook"),
            adapter=discord.AsyncWebhookAdapter(self.session)
        )
        self.guild_webhook = discord.Webhook.from_url(
            self.from_config("guild_webhook"),
            adapter=discord.AsyncWebhookAdapter(self.session)
        )

        self.ctx_cache = {}
        self.cmd_usage = 0
        self.loop.create_task(self.chunk_all_guilds())

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

        for guild in self.guilds:
            get_guild = await self.pool.fetchval(
                "SELECT guild_id FROM guild_settings WHERE guild_id = $1", guild.id
            )

            if get_guild is None:
                await self.pool.execute(
                    "INSERT INTO guild_settings VALUES($1, DEFAULT, $2, $3, $4)",
                    guild.id, None, None, False
                )

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

            await set_giveaway(self, entry["ends_at"], entry["channel_id"], entry["message_id"])

        logger.info("Finished caching and setting giveaways")

        mutes = await self.pool.fetch("SELECT * FROM guild_mutes")
        for mute in mutes:
            now = time.time()
            seconds_left = mute["end_time"] - now
            await set_mute(bot=self,
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

        await self.change_presence(activity=discord.Game(name=self.from_config("status")))

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

    def api_key_for(self, service: str) -> str:
        config = toml.load("./config.toml")
        api_keys = config["api-keys"]

        return api_keys[service]

    def bot_token_for(self, type: str) -> str:
        config = toml.load("./config.toml")
        tokens = config["tokens"]

        return tokens[type]

    def from_config(self, what: str) -> str:
        config = toml.load("./config.toml")
        misc = config["misc"]

        return misc[what]

    def database_for(self, what: str) -> dict:
        config = toml.load("./config.toml")
        database = config["database"]

        return database[what]

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
            reaction, user = await self.wait_for(
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
