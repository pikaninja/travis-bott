import asyncio
import re
import time

import asyncpg
import discord
from discord.ext import commands

from datetime import datetime as dt
from datetime import timedelta

import aiohttp

from .customcontext import CustomContext
from .utils import set_mute

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
        self.verification_config = {}

        self.loop = asyncio.get_event_loop()
        self.pool = self.loop.run_until_complete(
            asyncpg.create_pool(**cfg.POSTGRES_INFO)
        )

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.loop.create_task(self.do_prep())
        self.loop.create_task(self.update_web_stats())
        self.announcement = {
            "title": None,
            "message": None
        }
        self.maintenance_mode = False
        self.add_check(self.command_check)
        self.add_check(self.blacklist_check)

        self.support_url = "https://discord.gg/tKZbxAF"
        self.invite_url = discord.utils.oauth_url(
            "706530005169209386", discord.Permissions(2080763126))
        self.github_url = "https://github.com/platform-discord/travis-bott"

        self.blacklist = {}

    @property
    async def kal(self):
        return self.get_user(self.owner_id)

    async def close(self):
        await super().close()
        await self.session.close()
        await self.pool.close()

    async def do_prep(self):
        await self.wait_until_ready()
        verification_config = await self.pool.fetch("SELECT message_id, role_id FROM guild_verification")
        guild_configs = await self.pool.fetch("SELECT * FROM guild_settings")
        blacklist = await self.pool.fetch("SELECT * FROM blacklist")

        for entry in verification_config:
            self.verification_config[entry["message_id"]] = entry["role_id"]

        for entry in guild_configs:
            data = {
                "guild_prefix": entry["guild_prefix"],
                "mute_role_id": entry["mute_role_id"],
                "log_channel": entry["log_channel"]
            }

            self.config[entry["guild_id"]] = data

        for entry in blacklist:
            self.blacklist[entry["id"]] = entry["reason"]

        mutes = await self.pool.fetch("SELECT * FROM guild_mutes")
        for mute in mutes:
            now = time.time()
            seconds_left = mute["end_time"] - now
            await set_mute(bot=self,
                           guild_id=mute["guild_id"],
                           user_id=mute["member_id"],
                           _time=seconds_left)

        updates_channel = await self.fetch_channel(711586681580552232)
        last_update = await updates_channel.fetch_message(updates_channel.last_message_id)
        cool = last_update.content.split("\n")
        update = {
            "title": cool[0],
            "message": "\n".join(cool[1:])
        }

        self.announcement = update

    async def update_web_stats(self):
        await self.wait_until_ready()
        while True:
            users = sum(g.member_count for g in self.guilds)
            cmds = len([x for x in self.walk_commands()])
            guilds = len(self.guilds)

            await self.pool.execute("UPDATE web_stats SET users = $1, commands = $2, guilds = $3",
                                    users, cmds, guilds)

            await asyncio.sleep(300)

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    async def on_message(self, message):
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
            "INSERT INTO guild_settings(guild_id, guild_prefix) VALUES($1, $2)",
            guild.id,
            "tb!",
        )
        self.config[guild.id] = {
            "guild_prefix": "tb!",
            "mute_role_id": None,
            "log_channel": None
        }

        message = [
            f"I was just added to {guild.name} with {guild.member_count} members.",
            f"Now in {len(self.guilds)} guilds.",
        ]
        url = cfg.guild_log_webhook
        data = {
            "username": "Added to guild.",
            "content": "\n".join(message)
        }

        await self.session.post(url, data=data)

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
        url = cfg.guild_log_webhook
        data = {
            "username": "Removed from guild.",
            "content": "\n".join(message)
        }

        await self.session.post(url, data=data)

    async def on_message_edit(self, before, after):
        await self.process_commands(after)

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
