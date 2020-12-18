import KalDiscordUtils
from discord.ext import commands

import discord

import utils
import asyncio


class Prefix(commands.Converter):
    async def convert(self, ctx, argument):
        if len(argument) == 0:
            return "tb!"

        if argument == "None":
            return "tb!"
        if argument == "[BLANK]":
            return ""
        else:
            return argument


class Management(utils.BaseCog, name="management"):
    """Management Commands"""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member.bot:
            return

        if payload.emoji.name != "✅":
            return

        try:
            role_id = self.bot.verification_config[payload.message_id]
        except KeyError:
            return

        guild = await self.bot.fetch_guild(payload.guild_id)
        role = guild.get_role(role_id)

        if role is None:
            del self.bot.verification_config[payload.message_id]
            await self.bot.pool.execute("DELETE FROM guild_verification WHERE message_id = $1",
                                        payload.message_id)

        await payload.member.add_roles(role, reason="Reaction Verification")

    # @commands.group(invoke_without_command=True)
    # @commands.guild_only()
    # @commands.has_permissions(manage_guild=True)
    # @commands.bot_has_permissions(manage_roles=True)
    # async def autoreact(self, ctx):
    #     """Activates the user-interactive menu to set up an auto-react event."""

    #     instance = AutoReactMenu()
    #     await instance.paginate(ctx)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def roles(self, ctx: utils.CustomContext):
        """Set up for premium roles for the guild"""

        await ctx.send_help(ctx.command)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx: utils.CustomContext):
        """Shows you all of the configuration for the current server."""

        embed = KalDiscordUtils.Embed.default(ctx)

        mapped_names = {
            "guild_prefix": "Current Prefix",
            "mute_role_id": "Mute Role ID",
            "log_channel": "Logging Channel ID",
        }

        for k, v in self.bot.config[ctx.guild.id].items():
            name = mapped_names.get(k)
            embed.add_field(name=name,
                            value=f"`{v}`",
                            inline=False)

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def superlogs(self, ctx: utils.CustomContext, channel: discord.TextChannel):
        """Sets the channel that all of Travis' logs go to."""

        await self.bot.pool.execute(
            "UPDATE guild_settings SET log_channel = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )

        self.bot.config[ctx.guild.id]["log_channel"] = channel.id
        await ctx.send(f"Successfully set {channel.mention} to the super-logs channel.")

    @superlogs.command(name="off")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def superlogs_off(self, ctx: utils.CustomContext):
        """Removes the superlog channel off Travis."""

        try:
            log_channel_id = self.bot.config[ctx.guild.id]["log_channel"]
        except KeyError:
            return await ctx.send("You do not have super-logging enabled in this guild.")

        await self.bot.pool.execute(
            "UPDATE guild_settings SET log_channel = $1 WHERE guild_id = $2",
            None,
            ctx.guild.id,
        )

        del self.bot.config[ctx.guild.id]["log_channel"]
        await ctx.send(f"Successfully removed the logging channel for this guild.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def muterole(self, ctx: utils.CustomContext, role: str = None):
        """Sets the mute role for the server."""

        if role is None:
            current_mute_role = await self.bot.pool.fetchval(
                "SELECT mute_role_id FROM guild_settings WHERE guild_id = $1",
                ctx.guild.id,
            )
            if current_mute_role is None:
                return await ctx.send_help(ctx.command)
            role = ctx.guild.get_role(current_mute_role)
            fmt = f"Your current mute role is: {role.name}, ID: {role.id}.\nYou can set a new mute role using {ctx.prefix}muterole <Role>"
            return await ctx.send(fmt)

        await ctx.send(
            "This will deny this role from being able to speak in all channels, are you sure you want this to be your mute role?"
        )

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
            await self.bot.pool.execute(
                "UPDATE guild_settings SET mute_role_id = $1 WHERE guild_id = $2",
                role.id,
                ctx.guild.id,
            )
            await ctx.send(
                f"Mute role has been set up and permissions have been changed in {count} channels."
            )

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx: utils.CustomContext):
        """Gets the current prefix."""

        prefix = self.bot.config[ctx.guild.id]["guild_prefix"]
        await ctx.send(f"The current prefix for this server is: `{prefix}`")

    @prefix.command(name="set")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: utils.CustomContext, prefix: Prefix):
        """To reset input \"None\",
        for a blank prefix do:
        {prefix}prefix set [BLANK]

        Permissions needed: `Manage Server`"""

        if len(prefix) > 10:
            return await ctx.send("❌ The prefix can not be above 10 characters.")

        _id = ctx.bot.user.id
        if prefix.startswith((f"<@!{_id}>", f"<@{_id}>")):
            return await ctx.send("That prefix is reserved/already in use.")

        await self.bot.pool.execute(
            "UPDATE guild_settings SET guild_prefix = $1 WHERE guild_id = $2",
            prefix,
            ctx.guild.id,
        )
        self.bot.config[ctx.guild.id]["guild_prefix"] = prefix
        await ctx.thumbsup()

    @commands.group(aliases=["verify"], invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    async def verification(self, ctx: utils.CustomContext):
        """Verification Setup.
        Permissions needed: `Manage Server`
        """

        return await ctx.send_help(ctx.command)

    @verification.command(name="setup")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    async def verification_setup(self, ctx: utils.CustomContext, channel: discord.TextChannel, *, role: str):
        """Goes through the process to set up verification."""

        check_guild = await self.bot.pool.fetchrow(
            "SELECT * FROM guild_verification WHERE guild_id = $1", ctx.guild.id
        )

        if check_guild:
            return await ctx.send("❌ Verification is already set up.")

        embed = KalDiscordUtils.Embed.default(
            ctx,
            title="Human Verification",
            description="React to this message to gain access to the rest of the server.",
        )

        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.timestamp = discord.Embed.Empty

        role = await utils.find_roles(ctx.guild, role)
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await self.bot.pool.execute(
            "INSERT INTO guild_verification(guild_id, message_id, role_id) VALUES($1, $2, $3)",
            ctx.guild.id,
            msg.id,
            role.id,
        )
        self.bot.verification_config[msg.id] = role.id

        await ctx.thumbsup()

    @verification.command(name="reset")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def verification_reset(self, ctx: utils.CustomContext):
        """Resets verification in the server."""

        check_guild = await self.bot.pool.fetchrow(
            "SELECT * FROM guild_verification WHERE guild_id = $1", ctx.guild.id
        )

        if not check_guild:
            return await ctx.send("❌ You do not have verification set up.")

        msg_id = await self.bot.pool.fetchval("SELECT message_id FROM guild_verification WHERE guild_id = $1",
                                              ctx.guild.id)

        await self.bot.pool.execute(
            "DELETE FROM guild_verification WHERE guild_id = $1", ctx.guild.id
        )
        del self.bot.verification_config[msg_id]

        await ctx.thumbsup()


def setup(bot):
    bot.add_cog(Management(bot, "🛡 Management"))
