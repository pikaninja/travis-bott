from discord.ext import commands

import discord

from utils import db
from utils.CustomBot import MyBot

class VerificationReaction(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member.bot:
            return
        
        guild_settings = await db.record("SELECT * FROM guild_verification WHERE guild_id = ?", payload.guild_id)

        if not guild_settings:
            return

        guild = await self.bot.fetch_guild(guild_settings[0])
        role = guild.get_role(guild_settings[2])
        
        if payload.message_id != guild_settings[1]:
            return
        
        if payload.emoji.name != "✅":
            return

        await payload.member.add_roles(role, reason="Human Verification")

def setup(bot):
    bot.add_cog(VerificationReaction(bot))