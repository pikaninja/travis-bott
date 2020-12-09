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

        current_mute_role_id = await self.bot.pool.fetchval(
            "SELECT mute_role_id FROM guild_settings WHERE guild_id = $1", ctx.guild.id
        )
        verification_role_id = await self.bot.pool.fetchval(
            "SELECT role_id FROM guild_verification WHERE guild_id = $1", ctx.guild.id
        )
        super_logs_channel_id = await self.bot.pool.fetchval(
            "SELECT log_channel FROM guild_settings WHERE guild_id = $1", ctx.guild.id
        )
        prefix = self.bot.cache["prefixes"][ctx.guild.id]

        fields = [
            [
                "Mute Role",
                ctx.guild.get_role(current_mute_role_id).mention
                if current_mute_role_id
                else "No role set.",
            ],
            [
                "Verification Role",
                ctx.guild.get_role(verification_role_id).mention
                if verification_role_id
                else "No role set.",
            ],
            [
                "Super Logging Channel",
                ctx.guild.get_channel(super_logs_channel_id).mention
                if super_logs_channel_id
                else "No channel set.",
            ],
            ["Current prefix:", f"`{prefix}`"],
        ]

        embed = utils.Embed.default(
            ctx,
            title=f"Configuration for {ctx.guild}"
        )

        for k, v in fields:
            embed.add_field(
                name=k, value=v if v else "None set.", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
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

        await ctx.send(f"Successfully set {channel.mention} to the super-logs channel.")

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

        prefix = self.bot.cache["prefixes"][ctx.guild.id]
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
        self.bot.cache["prefixes"][ctx.guild.id] = prefix
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

        embed = utils.Embed.default(
            ctx,
            title="Human Verification",
            description="React to this message to gain access to the rest of the server.",
        )

        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)

        role = await utils.find_roles(ctx.guild, role)
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await self.bot.pool.execute(
            "INSERT INTO guild_verification(guild_id, message_id, role_id) VALUES($1, $2, $3)",
            ctx.guild.id,
            msg.id,
            role.id,
        )
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

        await self.bot.pool.execute(
            "DELETE FROM guild_verification WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.thumbsup()


def setup(bot):
    bot.add_cog(Management(bot, "🛡 Management"))
