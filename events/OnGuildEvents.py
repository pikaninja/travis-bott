from discord.ext import commands
import discord

from utils import db


class OnGuildEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.pool.execute(
            "INSERT INTO guild_settings(guild_id, guild_prefix) VALUES($1, $2)",
            guild.id,
            "tb!",
        )
        self.bot.cache["prefixes"][guild.id] = "tb!"

        await db.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.pool.execute(
            "DELETE FROM guild_settings WHERE guild_id = $1", guild.id
        )
        await self.bot.pool.execute(
            "DELETE FROM guild_mutes WHERE guild_id = $1", guild.id
        )

        del self.bot.cache["prefixes"][guild.id]

        await db.commit()


def setup(bot):
    bot.add_cog(OnGuildEvents(bot))
