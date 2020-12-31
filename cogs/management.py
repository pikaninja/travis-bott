"""
Commands to provide server managers some powerful tools.
Copyright (C) 2020 kal-byte

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import random

import dateparser

import discord

import utils
import asyncio

from discord.ext import commands

from utils.embed import Embed


class Prefix(commands.Converter):
    async def convert(self, ctx: utils.CustomContext, argument: str):
        if len(argument) == 0:
            return "tb!"

        if argument.startswith(" "):
            return "".join(argument.split()) + " " if argument.endswith(" ") else ""
        if argument == "None":
            return "tb!"
        if argument == "[BLANK]":
            return ""
        else:
            return argument


class GiveawayQuestions:

    @staticmethod
    async def what_channel(ctx: utils.CustomContext, name_or_id: str):
        converter = commands.TextChannelConverter()

        try:
            channel = await converter.convert(ctx, name_or_id)
        except commands.ChannelNotFound:
            raise commands.BadArgument(
                "I couldn't find that channel! You must restart the interactive giveaway.")

        return channel, "channel"

    @staticmethod
    async def time_end(ctx: utils.CustomContext, time_end: str):
        if not time_end.startswith("in "):
            time_end = f"in {time_end}"

        if not time_end.endswith(" UTC"):
            time_end = f"{time_end} UTC"

        parsed_time = dateparser.parse(time_end)

        if parsed_time is None:
            raise commands.BadArgument("You did not input a valid time.")

        return parsed_time, "time_end"

    @staticmethod
    async def get_prize(ctx: utils.CustomContext, what_prize: str):

        return what_prize, "prize"

    @staticmethod
    async def get_role_needed(ctx: utils.CustomContext, what_role: str):
        if what_role.lower() == "none":
            return "None", "role_needed"

        converter = utils.RoleConverter()
        role = await converter.convert(ctx, what_role)

        return role, "role_needed"


class Management(utils.BaseCog, name="management"):
    """Management Commands"""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name
        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

    # noinspection PyUnresolvedReferences
    @commands.Cog.listener("on_guild_channel_create")
    async def add_mute_new_channel(self, channel: discord.abc.GuildChannel):
        """Updated the new channels mute perms once created if the guild has a mute role set."""

        try:
            mute_role_id = self.bot.config[channel.guild.id]["mute_role_id"]
        except KeyError:
            return

        role = channel.guild.get_role(mute_role_id)

        if role is None:
            await self.bot.pool.execute("UPDATE guild_settings SET mute_role_id = NULL WHERE guild_id = $1",
                                        channel.guild.id)
            self.bot.config[channel.guild.id]["mute_role_id"] = None

        role_overwrites = channel.overwrites_for(role)
        role_overwrites.update(send_messages=False)

        try:
            await channel.set_permissions(
                target=role,
                overwrite=role_overwrites,
                reason="Disable mute role permissions to talk in this channel."
            )
        except:
            pass

    @commands.Cog.listener()
    async def on_giveaway_end(self, message: discord.PartialMessage):
        message: discord.Message = await message.fetch()

        reaction: discord.Reaction = message.reactions[0]
        try:
            users = [user async for user in reaction.users().filter(lambda u: not u.bot)]
            random_user = random.choice(users)
        except IndexError:
            fmt = f"No one entered into [this]({message.jump_url}) giveaway :("
            embed = discord.Embed()
            embed.description = fmt

            return await message.channel.send(embed=embed)

        fmt = f"The winner of [this]({message.jump_url}) giveaway is: {random_user.mention}"
        embed = discord.Embed()
        embed.description = fmt

        await message.channel.send(
            f"Congratulations to {random_user.mention}",
            embed=embed
        )

    @commands.Cog.listener("on_raw_reaction_add")
    async def check_if_has_role(self, payload: discord.RawReactionActionEvent):
        if payload.member.bot:
            return

        try:
            role_id = self.bot.giveaway_roles[payload.message_id]
        except KeyError:
            return

        if role_id not in payload.member._roles:
            channel = await self.bot.fetch_channel(payload.channel_id)

            message = await (discord.PartialMessage(channel=channel, id=payload.message_id)).fetch()
            reaction = message.reactions[0]

            await reaction.remove(payload.member)

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

    @commands.command(aliases=["sgw"])
    @commands.has_permissions(manage_guild=True)
    async def startgiveaway(self, ctx: utils.CustomContext):
        """Starts an interactive giveaway message."""

        questions = {
            "What channel would you like the giveaway to be in?": GiveawayQuestions.what_channel,
            "When will the giveaway end?": GiveawayQuestions.time_end,
            "What will the prize be?": GiveawayQuestions.get_prize,
            "What role will be required? Type `none` if one isn't required.": GiveawayQuestions.get_role_needed,
        }

        what_is_needed = {
            "channel": None,
            "time_end": None,
            "prize": None,
            "role_needed": None
        }

        for question, func in questions.items():
            await ctx.send(question, new_message=True)
            try:
                response = await self.bot.wait_for("message",
                                                   timeout=30.0,
                                                   check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            except asyncio.TimeoutError:
                return await ctx.send("You did not reply in time!", new_message=True)
            else:
                get_thing, what_thing = await func(ctx, response.content)
                what_is_needed[what_thing] = get_thing

        time_end = what_is_needed['time_end']
        role_needed = what_is_needed['role_needed']
        channel = what_is_needed['channel']

        embed = Embed.default(ctx)
        embed.title = f"Giveaway for {what_is_needed['prize']}"

        fmt = f"React to \N{PARTY POPPER} to be entered into the giveaway."
        fmt += f"\nRole needed: {role_needed.mention}" if role_needed != "None" else ''

        embed.description = fmt

        embed.set_footer(text="Ends at:", icon_url=ctx.guild.icon_url)
        embed.timestamp = time_end

        message = await channel.send(embed=embed)
        await message.add_reaction("\N{PARTY POPPER}")

        if role_needed == "None":
            query = "INSERT INTO giveaways VALUES($1, $2, $3)"
            values = message.id, ctx.channel.id, time_end.replace(tzinfo=None)
        else:
            query = "INSERT INTO giveaways VALUES($1, $2, $3, $4)"
            values = message.id, ctx.channel.id, time_end.replace(
                tzinfo=None), role_needed.id

        await self.bot.pool.execute(query, *values)

        if role_needed != "None":
            self.bot.giveaway_roles[message.id] = role_needed.id

        await utils.set_giveaway(self.bot, time_end, channel.id, message.id)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def roles(self, ctx: utils.CustomContext):
        """Set up for premium roles for the guild"""

        await ctx.send_help(ctx.command)

    @commands.command(aliases=["cfg"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx: utils.CustomContext):
        """Shows you all of the configuration for the current server."""

        embed = Embed.default(ctx)

        mapped_names = {
            "guild_prefix": "Current Prefix",
            "mute_role_id": "Mute Role ID",
            "log_channel": "Logging Channel ID",
            "owoify": "Owoified Texts",
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
    async def muterole(self, ctx: utils.CustomContext, role: utils.RoleConverter = None):
        """Sets the mute role for the server."""

        if role is None:
            try:
                mute_role_id = self.bot.config[ctx.guild.id]["mute_role_id"]
            except KeyError:
                fmt = (
                    f"There is no mute role set for this server... set one using "
                    "`{ctx.prefix}muterole [Role Name Here]`"
                )
                return await ctx.send(fmt)

            role = ctx.guild.get_role(mute_role_id)
            fmt = f"Your current mute role is: {role} (ID: {role.id})"
            return await ctx.send(fmt)

        await ctx.send(
            f"You chose `{role}` to be set as your mute role, by typing `yes` this will make it so that the role "
            "can *not* type in any channel and this action can not be reversed. Please type `yes` or `no`",
            new_message=True
        )

        try:
            message = await self.bot.wait_for(
                "message",
                timeout=30.0,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
        except asyncio.TimeoutError:
            return await ctx.send("You did not reply in time.",
                                  new_message=True)
        else:
            content = message.content.lower()
            if content == "yes":
                await self.bot.pool.execute("UPDATE guild_settings SET mute_role_id = $1 WHERE guild_id = $2",
                                            role.id, ctx.guild.id)
                self.bot.config[ctx.guild.id]["mute_role_id"] = role.id

                await ctx.send("Alright, this may take a while.", new_message=True)

                for channel in ctx.guild.channels:
                    perms = channel.overwrites_for(role)
                    perms.update(send_messages=False)
                    try:
                        await channel.set_permissions(
                            target=role,
                            overwrite=perms,
                            reason=f"Mute role set by: {ctx.author}"
                        )
                    except discord.Forbidden:
                        return await ctx.send("I must have permissions to edit channel permissions to do this!",
                                              new_message=True)

                return await ctx.reply("Finished updating all channel permissions for that role.")
            else:
                return await ctx.send("Alright, backing out.",
                                      new_message=True)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def owoify(self, ctx: utils.CustomContext, enabled: bool):
        """Enables owoified text for the server."""

        self.bot.config[ctx.guild.id]["owoify"] = enabled
        await self.bot.pool.execute("UPDATE guild_settings SET owoify = $1 WHERE guild_id = $2",
                                    enabled, ctx.guild.id)

        await ctx.send("Successfully updated your owoify settings")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def prefix(self, ctx: utils.CustomContext):
        """Gets the current prefix."""

        try:
            prefix = self.bot.config[ctx.guild.id]["guild_prefix"]
        except AttributeError:
            prefix = "tb!"
            
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
    async def verification_setup(self, ctx: utils.CustomContext, channel: discord.TextChannel, *, role: utils.RoleConverter):
        """Goes through the process to set up verification."""

        check_guild = await self.bot.pool.fetchrow(
            "SELECT * FROM guild_verification WHERE guild_id = $1", ctx.guild.id
        )

        if check_guild:
            return await ctx.send("❌ Verification is already set up.")

        embed = Embed.default(
            ctx,
            title="Human Verification",
            description="React to this message to gain access to the rest of the server.",
        )

        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.timestamp = discord.Embed.Empty

        try:
            msg = await channel.send(embed=embed)
        except discord.Forbidden:
            return await ctx.send("I can not send messages in that channel, please give me permissions to!")

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
