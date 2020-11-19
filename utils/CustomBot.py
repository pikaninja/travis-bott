import asyncio
import json

import asyncpg
import discord
from discord.ext import commands

from datetime import datetime as dt
from datetime import timedelta

import aiohttp

from utils.CustomContext import CustomContext

import config as cfg

from decouple import config


async def get_prefix(bot: commands.AutoShardedBot, message: discord.Message):
    if (
        message.author.id == bot.owner_id and
            message.content.startswith(("dev", "jsk"))
    ):
        return ""
    if message.guild is None:
        return commands.when_mentioned_or("tb!")(bot, message)
    else:
        prefix = bot.cache["prefixes"][message.guild.id]
        return commands.when_mentioned_or(prefix)(bot, message)


class MyBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(get_prefix, *args, **kwargs)

        self.start_time = dt.now()
        self.cache = {}
        self.disabled_commands = {}

        self.loop = asyncio.get_event_loop()
        self.pool = self.loop.run_until_complete(
            asyncpg.create_pool(**cfg.POSTGRES_INFO)
        )

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.loop.create_task(self.cache_prefixes())
        self.loop.create_task(self.cache_premiums())
        self.loop.create_task(self.get_announcement())
        self.announcement = {
            "title": None,
            "message": None
        }

    async def close(self):
        await self.session.close()
        await self.pool.close()
        await super().close()

    async def get_announcement(self):
        with open("./announcement.json") as f:
            data = json.load(f)
            self.announcement = data

    async def cache_prefixes(self):
        all_prefixes = await self.pool.fetch(
            "SELECT guild_id, guild_prefix FROM guild_settings"
        )
        prefixes = {}
        for entry in all_prefixes:
            prefixes[entry["guild_id"]] = entry["guild_prefix"]
        self.cache["prefixes"] = prefixes

    async def cache_premiums(self):
        rows = await self.pool.fetch("SELECT * FROM premium")
        premiums = {}
        for row in rows:
            guild_id = row["guild_id"]
            end_time = row["end_time"]
            premiums[guild_id] = end_time
        self.cache["premium_guilds"] = premiums

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    async def on_message(self, message):
        if not self.is_ready():
            return

        if (
            message.content == f"<@!{self.user.id}>"
            or message.content == f"<@{self.user.id}>"
        ):
            prefix = self.cache["prefixes"][message.guild.id]
            await message.channel.send(
                "Hey I saw you mentioned me, incase you didn't know my prefix "
                f"here is `{prefix}`."
            )

        await self.process_commands(message)

    async def on_message_edit(self, before, after):
        if before.content != after.content:
            ctx = await self.get_context(after)
            await self.invoke(ctx)

    def get_uptime(self) -> timedelta:
        """Gets the uptime of the bot"""

        return timedelta(seconds=int((dt.now() - self.start_time).total_seconds()))

    async def config(self, guild_id: int, table: str) -> str:
        """Get all records of a specific guild at a specific table"""

        records = await self.pool.fetch(
            f"SELECT * FROM {table} WHERE guild_id = $1", guild_id
        )
        return records[0]
