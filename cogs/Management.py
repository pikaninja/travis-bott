from discord.ext import commands

import discord

from utils import db, utils
import asyncio

class Management(commands.Cog, name="🛡 Management"):
    """Management Commands"""
    def __init__(self, bot):
        self.bot = bot

    # @commands.command()
    # @commands.guild_only()
    # @commands.has_permissions(manage_guild=True)
    # @commands.bot_has_permissions(manage_roles=True)
    # async def

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx):
        """Shows you all of the configuration for the current server."""

        current_mute_role_id = await db.field("SELECT mute_role_id FROM guild_settings WHERE guild_id = ?", ctx.guild.id)
        verification_role_id = await db.field("SELECT role_id FROM guild_verification WHERE guild_id = ?", ctx.guild.id)
        super_logs_channel_id = await db.field("SELECT log_channel FROM guild_settings WHERE guild_id = ?", ctx.guild.id)
        prefix = self.bot.prefixes[ctx.guild.id]

        fields = [
            ["Mute Role", ctx.guild.get_role(current_mute_role_id).mention if current_mute_role_id else "No role set."],
            ["Verification Role", ctx.guild.get_role(verification_role_id).mention if verification_role_id else "No role set."],
            ["Super Logging Channel", ctx.guild.get_channel(super_logs_channel_id).mention if super_logs_channel_id else "No channel set."],
            ["Current prefix:", f"`{prefix}`"]
        ]

        embed = utils.embed_message(title=f"Configuration for {ctx.guild}")

        for k, v in fields:
            embed.add_field(name=k, value=v if v else "None set.", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def superlogs(self, ctx, channel: discord.TextChannel):
        """Sets the channel that all of Travis' logs go to."""

        await db.execute("UPDATE guild_settings SET log_channel = ? WHERE guild_id = ?", channel.id, ctx.guild.id)
        await db.commit()

        await ctx.send(f"Successfully set {channel.mention} to the super-logs channel.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def muterole(self, ctx, role: str = None):
        """Sets the mute role for the server."""

        if role is None:
            current_mute_role = await db.field("SELECT mute_role_id FROM guild_settings WHERE guild_id = ?", ctx.guild.id)
            if current_mute_role is None:
                return await ctx.send_help(ctx.command)
            role = ctx.guild.get_role(current_mute_role)
            fmt = f"Your current mute role is: {role.name}, ID: {role.id}.\nYou can set a new mute role using {ctx.prefix}muterole <Role>"
            return await ctx.send(fmt)

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
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx):
        """Gets the current prefix."""

        prefix = self.bot.prefixes[ctx.guild.id]
        await ctx.send(f"The current prefix for this server is: `{prefix}`")
    
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
        await self.bot.cache_prefixes()
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

    @verification.command(name="interactive")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def verification_interaction(self, ctx):
        """__**PREMIUM**__ Goes through a more customizable, interactive version of verification."""

        check_guild = await db.record("SELECT * FROM guild_verification WHERE guild_id = ?", ctx.guild.id)

        if check_guild:
            return await ctx.send("❌ Verification is already set up.")
    
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