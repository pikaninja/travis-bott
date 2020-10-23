import aiohttp
from discord.ext import commands
import discord

import config as cfg


class BotJoinLeave(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        message = [
            f"I was just added to {guild.name} with {guild.member_count} members.",
            f"Now in {len(self.bot.guilds)} guilds.",
        ]
        url = cfg.guild_log_webhook
        data = {}
        data["content"] = "\n".join(message)
        data["username"] = "Added to guild."

        async with aiohttp.ClientSession() as session:
            await session.post(url, data=data)
            await session.close()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        message = [
            f"I was just removed from {guild.name} with {guild.member_count} members.",
            f"Now in {len(self.bot.guilds)} guilds.",
        ]
        url = cfg.guild_log_webhook
        data = {}
        data["content"] = "\n".join(message)
        data["username"] = "Removed from guild."

        async with aiohttp.ClientSession() as session:
            await session.post(url, data=data)
            await session.close()


def setup(bot):
    bot.add_cog(BotJoinLeave(bot))
