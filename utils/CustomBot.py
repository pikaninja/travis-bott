import discord
from discord.ext import commands

from datetime import datetime as dt
from datetime import timedelta

from utils import db
from utils.CustomContext import CustomContext

async def get_prefix(bot: commands.AutoShardedBot, message: discord.Message):
    if message.guild is None:
        return "tb!"
    else:
        prefix = await db.field("SELECT guild_prefix FROM guild_settings WHERE guild_id = ?", message.guild.id)
        return commands.when_mentioned_or(prefix)(bot, message)

class MyBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(get_prefix, *args, **kwargs)

        self.start_time = dt.now()

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    async def on_message(self, message):
        if not self.is_ready():
            return

        await self.process_commands(message)

    def get_uptime(self) -> timedelta:
        """Gets the uptime of the bot"""

        return timedelta(seconds=int((dt.now() - self.start_time).total_seconds()))
    
    async def config(self, guild_id: int, table: str) -> str:
        """Get all records of a specific guild at a specific table"""

        records = await db.records(f"SELECT * FROM {table} WHERE guild_id = ?", guild_id)
        return records[0]