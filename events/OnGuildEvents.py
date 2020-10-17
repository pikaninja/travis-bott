from discord.ext import commands
import discord

from utils import db

class OnGuildEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await db.execute(f"INSERT INTO guild_settings(guild_id, guild_prefix) VALUES(?, ?)", guild.id, "tb!")
        self.bot.prefixes[guild.id] = "tb!"

        await db.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await db.execute(f"DELETE FROM guild_settings WHERE guild_id = ?", guild.id)
        await db.execute(f"DELETE FROM guild_mutes WHERE guild_id = ?", guild.id)

        del self.bot.prefixes[guild.id]

        await db.commit()

def setup(bot):
    bot.add_cog(OnGuildEvents(bot))