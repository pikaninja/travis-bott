from discord.ext import commands

import discord

from utils import db, utils
import asyncio

class Management(commands.Cog, name="🛡 Management"):
    """Management Commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def muterole(self, ctx, role: str):
        """Sets the mute role for the server."""

        await ctx.send("This will deny this role from being able to speak in all channels, are you sure you want this to be your mute role?")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            user_input = await ctx.bot.wait_for("message", timeout=10.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f"You ran out of time to answer {ctx.author.mention}")
        else:
            user_reply = user_input.content.lower()
            if not user_reply == "yes":
                return await ctx.send("Ok backing out.")
                
            role = await utils.find_roles(ctx.guild, role)
            if not role:
                return await ctx.send("I could not find that role.")
            await ctx.send("Ok this may take a few.")
            count = 0
            for c in ctx.guild.text_channels:
                await c.set_permissions(role, send_messages=False)
                count += 1
            await db.execute("UPDATE guild_settings SET mute_role_id = ? WHERE guild_id = ?", role.id, ctx.guild.id)
            await db.commit()
            await ctx.send(f"Mute role has been set up and permissions have been changed in {count} channels.")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def prefix(self, ctx):
        """Gets the current prefix."""

        await ctx.send(f"The current prefix for this server is: `{ctx.prefix}`")
    
    @prefix.command(name="set")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_set(self, ctx, prefix: str):
        """Sets a new prefix for the server.
        Permissions needed: `Manage Server`"""

        if len(prefix) == 0:
            return await ctx.send_help(ctx.command)

        if len(prefix) > 10:
            return await ctx.send("❌ The prefix can not be above 10 characters.")

        await db.execute("UPDATE guild_settings SET guild_prefix = ? WHERE guild_id = ?", prefix, ctx.guild.id)
        await db.commit()
        await ctx.thumbsup()

    @commands.group(aliases=["verify"], invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    async def verification(self, ctx):
        """Permissions needed: `Manage Server`
        Verification Setup."""

        return await ctx.send_help(ctx.command)
    
    @verification.command(name="setup")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    async def verification_setup(self, ctx, channel: discord.TextChannel, *, role: str):
        """Goes through the process to set up verification."""

        check_guild = await db.record("SELECT * FROM guild_verification WHERE guild_id = ?", ctx.guild.id)

        if check_guild:
            return await ctx.send("❌ Verification is already set up.")

        embed = utils.embed_message(title="Human Verification",
                                    message="React to this message to gain access to the rest of the server.",
                                    footer_text=ctx.guild.name,
                                    footer_icon=ctx.guild.icon_url)

        role = await utils.find_roles(ctx.guild, role)
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await db.execute("INSERT INTO guild_verification(guild_id, message_id, role_id) VALUES(?, ?, ?)",
                         ctx.guild.id, msg.id, role.id)
        await db.commit()
        await ctx.thumbsup()
    
    @verification.command(name="reset")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def verification_reset(self, ctx):
        """Resets verification in the server."""

        check_guild = await db.record("SELECT * FROM guild_verification WHERE guild_id = ?", ctx.guild.id)

        if not check_guild:
            return await ctx.send("❌ You do not have verification set up.")

        await db.execute("DELETE FROM guild_verification WHERE guild_id = ?", ctx.guild.id)
        await db.commit()
        await ctx.thumbsup()

def setup(bot):
    bot.add_cog(Management(bot))