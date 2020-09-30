from discord.ext import commands

import discord

from utils import db, utils

class ReactionRoles(commands.Cog, name="🎉 Reaction Roles"):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=["rr", "reactionroles"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def reaction_roles(self, ctx):
        """Sets up reaction roles for a specific message."""

        await ctx.send_help(ctx.command)

    @reaction_roles.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def rr_add(self, ctx, channel: discord.TextChannel, message_id: discord.Message, emoji: discord.PartialEmoji, *, role: str):
        """Adds a reaction role to a message."""

        role: discord.Role = await utils.find_roles(ctx.guild, role)
        
        check_msg = await db.record("SELECT * FROM reaction_roles WHERE guild_id = ? AND emoji_id = ? AND message_id = ? AND role_id = ?", ctx.guild.id, emoji.id, message_id, role.id)
        
        if check_msg:
            return await ctx.send("That reaction role is already on that message.")

        message: discord.Message = channel.fetch_message(message_id)

        await message.add_reaction(emoji)
        
        
def setup(bot):
    bot.add_cog(ReactionRoles(bot))