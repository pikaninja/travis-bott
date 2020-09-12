from discord.ext import commands
import discord

class BotJoinLeave(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        message = [f"I was just added to {guild.name} with {guild.member_count}", f"Now in {len(self.bot.guilds)} guilds."]
        channel: discord.TextChannel = self.bot.get_channel(710978375203946498)
        await channel.send("\n".join(message))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        message = [f"I was just removed from {guild.name} with {guild.member_count}", f"Now in {len(self.bot.guilds)} guilds."]
        channel: discord.TextChannel = self.bot.get_channel(710978375203946498)
        await channel.send("\n".join(message))

def setup(bot):
    bot.add_cog(BotJoinLeave(bot))