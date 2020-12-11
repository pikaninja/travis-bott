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


async def get_prefix(bot: commands.AutoShardedBot, message: discord.Message):
    if (
        bot.user.id == 706530005169209386 and
            message.author.id in bot.owner_ids and
        message.content.startswith(("dev", "jsk"))
    ):
        return ""
    if message.guild is None:
        return commands.when_mentioned_or("tb!")(bot, message)
    else:
        prefix = bot.config[message.guild.id]["guild_prefix"]
        return commands.when_mentioned_or(prefix)(bot, message)


class MyBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(get_prefix, *args, **kwargs)

        self.start_time = dt.now()
        self.config = {}

        self.loop = asyncio.get_event_loop()
        self.pool = self.loop.run_until_complete(
            asyncpg.create_pool(**cfg.POSTGRES_INFO)
        )

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.loop.create_task(self.cache_prefixes())
        self.loop.create_task(self.cache_premiums())
        self.loop.create_task(self.get_announcement())
        self.loop.create_task(self.update_web_stats())
        self.announcement = {
            "title": None,
            "message": None
        }

    @property
    async def kal(self):
        return self.get_user(self.owner_id)

    async def close(self):
        await super().close()
        await self.session.close()
        await self.pool.close()

    async def update_web_stats(self):
        await self.wait_until_ready()
        while True:
            users = sum(g.member_count for g in self.guilds)
            cmds = len([x for x in self.walk_commands()])
            guilds = len(self.guilds)

            await self.pool.execute("UPDATE web_stats SET users = $1, commands = $2, guilds = $3",
                                    users, cmds, guilds)

            await asyncio.sleep(300)

    async def get_announcement(self):
        await self.wait_until_ready()
        updates_channel = await self.fetch_channel(711586681580552232)
        last_update = await updates_channel.fetch_message(updates_channel.last_message_id)
        cool = last_update.content.split("\n")
        update = {
            "title": cool[0],
            "message": "\n".join(cool[1:])
        }

        self.announcement = update

    async def cache_prefixes(self):
        configs = await self.pool.fetch(
            "SELECT * FROM guild_settings"
        )
        for entry in configs:
            data = {
                "guild_prefix": entry["guild_prefix"],
                "mute_role_id": entry["mute_role_id"],
                "log_channel": entry["log_channel"]
            }
            self.config[entry["guild_id"]] = data

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
                "Hey I saw you mentioned me, in case you didn't know my prefix "
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

    async def reply(self, message_id, content=None, **kwargs):
        message = self._connection._get_message(message_id)
        await message.reply(content, **kwargs)

    async def add_delete_reaction(self, channel_id, message_id):
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
