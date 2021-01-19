"""
Moderation tools for moderators to utilize
Copyright (C) 2021 kal-byte

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

import datetime
import humanize

import utils
from utils.embed import Embed

from time import time as t

from datetime import datetime as dt
from discord.ext import commands, menus

import asyncio
import logging
import discord
import uuid
import re

time_regex = re.compile("(?:(\d{1,5})\s?(h|s|m|d))+?")
time_dict = {
    "h": 3600,
    "hours": 3600,
    "hour": 3600,
    "s": 1,
    "sec": 1,
    "secs": 1,
    "seconds": 1,
    "m": 60,
    "mins": 60,
    "minutes": 60,
    "min": 60,
    "d": 86400,
    "day": 86400,
    "days": 86400
}


class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        args = argument.lower()
        matches = re.findall(time_regex, args)
        _time = 0
        for v, k in matches:
            try:
                _time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument(
                    f"{k} is an invalid time-key! h/m/s/d are valid!")
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number!")
        return _time


class MemberOrID(commands.Converter):
    """Allows me to do some cool stuff with banning id's and such"""

    async def convert(self, ctx: utils.CustomContext, argument: str):
        try:
            member = await commands.MemberConverter().convert(ctx, argument)
        except commands.MemberNotFound:
            member = await commands.UserConverter().convert(ctx, argument)

            if member is None:
                raise commands.BadArgument("I couldn't find that user at all.")

        if isinstance(member, discord.Member):
            perms = ctx.channel.permissions_for(member)
            if perms.manage_messages:
                raise commands.BadArgument("That user is a staff member.")

        return member


class BannedUser(commands.Converter):
    """Gets a given banned user."""

    async def convert(self, ctx: utils.CustomContext, argument: str):
        try:
            user = await commands.UserConverter().convert(ctx, argument)
            try:
                await ctx.guild.fetch_ban(user)
            except discord.Forbidden:
                raise commands.BadArgument(
                    "I can't view that ban, this is probably due to my permissions.")
            except discord.NotFound:
                raise commands.BadArgument("That user is not banned.")
            except discord.HTTPException:
                raise commands.BadArgument(
                    "Discord messed up somewhere and I couldn't retrieve that ban.")

            return user
        except commands.UserNotFound:
            bans = await ctx.guild.bans()
            for ban in bans:
                if str(ban[1]).startswith(argument):
                    return ban[1]

        raise commands.BadArgument("Couldn't find that ban, sorry.")


class Role(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            role_converter = commands.RoleConverter()
            role = await role_converter.convert(ctx, argument)
        except commands.RoleNotFound:
            role = discord.utils.find(
                lambda r: r.name.lower().startswith(argument),
                ctx.guild.roles
            )

        if role is None:
            raise commands.RoleNotFound(f"Role \"{argument}\" not found.")

        return role


class ModerationsMenu(menus.ListPageSource):
    def __init__(self, data, *, per_page=5):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu: menus.Menu, page):
        embed = Embed.default(menu.ctx)
        embed.title = "Active Mutes"
        embed.description = "\n".join(page)

        return embed


class NotStaffMember(commands.Converter):
    async def convert(self, ctx, argument):
        converter = commands.MemberConverter()
        member = await converter.convert(ctx, argument)

        permissions = ctx.channel.permissions_for(member)

        if permissions.manage_messages:
            raise utils.MemberIsStaff("That member is a staff member...")
        else:
            return member


# noinspection PyUnresolvedReferences,PyMissingConstructor
class Moderation(utils.BaseCog, name="moderation"):
    """Moderation Commands"""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name

        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

    @commands.Cog.listener()
    async def on_mod_cmd(
            self,
            ctx: utils.CustomContext,
            action_type: str,
            moderator: discord.Member,
            user_affected: discord.Member,
            reason: str = None,
    ):
        """Dispatched manually by the Client.
        Contains:
        Action_type: Which is the type of action was done. This will be a string.
        Moderator: The moderator who carried out the actions, this will be of discord.Member.
        User_affected: The person who was affected within the actions, this will also be discord.Member.
        Reason: The reason provided in the action, if any. This will be a string."""

        try:
            log_channel_id = self.bot.config[ctx.guild.id]["log_channel"]
        except KeyError:
            return

        log_channel = await self.bot.fetch_channel(log_channel_id)

        if log_channel is None:
            del self.bot.config[ctx.guild.id]["log_channel"]
            await self.bot.pool.execute("UPDATE guild_settings SET log_channel = $1 WHERE guild_id = $2",
                                        None, ctx.guild.id)

        embed = Embed.default(
            ctx,
            title=f"Super Log",
            description=f"{moderator} to {user_affected}\n"
                        f"Command: {action_type}\n"
                        f"Reason: {reason or 'None'}",
        )

        embed.set_author(name=moderator.name, icon_url=moderator.avatar_url)

        await log_channel.send(embed=embed)

    @commands.Cog.listener("on_member_join")
    async def persistent_mutes(self, member: discord.Member):
        is_user_muted = await self.bot.pool.fetchrow("SELECT * FROM guild_mutes WHERE member_id = $1 AND guild_id = $2",
                                                     member.id, member.guild.id)

        if not is_user_muted:
            return

        mute_role_id = self.bot.config[member.guild.id]["guild_prefix"]
        mute_role = member.guild.get_role(role_id=mute_role_id)
        await member.add_roles(mute_role, reason="Mute Role Persist")

    @commands.command(aliases=["tban"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx: utils.CustomContext, user: NotStaffMember, how_long: utils.TimeConverter, *, reason: str):
        """Tempbans a user for a certain amount of time.
        e.g. `{prefix}tempban @kal#1806 5d Doing bad things excessively.`"""

        format_time = humanize.naturaldelta(how_long)
        await user.send(
            f"You were temporarily banned by {ctx.author} for the reason: {reason}. This ban expires in {format_time}"
        )

        sql = "INSERT INTO temp_bans VALUES($1, $2, $3, $4, $5, $6);"
        values = (str(uuid.uuid4()), ctx.guild.id,
                  ctx.author.id, user.id, reason, how_long)
        await self.bot.pool.execute(sql, *values)

        await user.ban(reason=reason)

        fmt = f"{user} was banned by {ctx.author} for {format_time} for the reason: {reason}"
        await ctx.send(fmt)

        ctx.bot.dispatch("mod_cmd", ctx, "temp-ban", ctx.author, user, reason)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: utils.CustomContext,
                   user: NotStaffMember, _time: TimeConverter,
                   *, reason: str):
        """Mutes a given user for an amount of time (e.g. 5s/5m/5h/5d)"""

        if _time < 5:
            return await ctx.send("You must provide a time that is 5 seconds or higher")

        try:
            mute_role_id = self.bot.config[ctx.guild.id]["mute_role_id"]
            mute_role = ctx.guild.get_role(mute_role_id)
        except KeyError:
            def predicate(r): return r.name.lower() == "muted"

            mute_role = discord.utils.find(
                predicate=predicate, seq=ctx.guild.roles)

            self.bot.config[ctx.guild.id]["mute_role_id"] = mute_role.id

            await self.bot.pool.execute("UPDATE guild_settings SET mute_role_id = $1 WHERE guild_id = $2",
                                        mute_role.id, ctx.guild.id)

        if mute_role is None:
            mute_role = await ctx.guild.create_role(name="Muted")

            await ctx.channel.set_permissions(mute_role, send_messages=False)

            await self.bot.pool.execute("UPDATE guild_settings SET mute_role_id = $1 WHERE guild_id = $2",
                                        mute_role.id, ctx.guild.id)

            self.bot.config[ctx.guild.id]["mute_role_id"] = mute_role.id

        await user.add_roles(mute_role, reason=f"Muted by: {ctx.author}")
        await utils.set_mute(bot=self.bot,
                             guild_id=ctx.guild.id,
                             user_id=user.id,
                             _time=_time)

        end_time = int(t() + _time)
        await self.bot.pool.execute("INSERT INTO guild_mutes VALUES($1, $2, $3)",
                                    ctx.guild.id, user.id, end_time)

        timestamp = t() + _time
        dt_obj = dt.fromtimestamp(timestamp)
        humanized = humanize.precisedelta(dt_obj, format="%0.0f")

        embed = Embed.default(ctx)
        embed.description = (
            f"{ctx.author.mention} ({ctx.author}) has muted {user.mention} ({user}) for {humanized} for the reason: "
            f"{reason}"
        )

        await ctx.send(embed=embed)
        ctx.bot.dispatch("mod_cmd", ctx, "mute", ctx.author, user, reason)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: utils.CustomContext, user: discord.Member):
        """Unmutes a given user if they have the guilds set muted role."""

        try:
            mute_role_id = self.bot.config[ctx.guild.id]["mute_role_id"]
            mute_role = ctx.guild.get_role(mute_role_id)
        except KeyError:
            def predicate(r): return r.name.lower() == "muted"
            mute_role = discord.utils.find(
                predicate=predicate, seq=ctx.guild.roles)

            self.bot.config[ctx.guild.id]["mute_role_id"] = mute_role.id

            await self.bot.pool.execute("UPDATE guild_settings SET mute_role_id = $1 WHERE guild_id = $2",
                                        mute_role.id, ctx.guild.id)

        if mute_role not in user.roles:
            return await ctx.send("That user does not have the guilds set muted role.")

        await user.remove_roles(mute_role, reason=f"Unmuted by: {ctx.author}")
        embed = Embed.default(ctx)
        embed.description = f"{ctx.author.mention} ({ctx.author}) unmuted {user.mention} ({user})"

        await ctx.send(embed=embed)
        ctx.bot.dispatch("mod_cmd", ctx, "unmute", ctx.author, user, None)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def moderations(self, ctx: utils.CustomContext):
        """Gets all of the current active mutes."""

        mutes = await self.bot.pool.fetch("SELECT * FROM guild_mutes WHERE guild_id = $1",
                                          ctx.guild.id)

        fmt = []

        for mute in mutes:
            user = ctx.guild.get_member(mute["member_id"])
            dt_obj = dt.fromtimestamp(mute["end_time"])
            humanized = humanize.precisedelta(dt_obj, format="%0.0f")
            fmt.append(f"{user} | {humanized}")

        menu = utils.KalPages(ModerationsMenu(fmt), clear_reactions_after=True)
        await menu.start(ctx)

    # @commands.command()
    # @commands.guild_only()
    # @commands.has_permissions(manage_messages=True)
    # @commands.bot_has_permissions(send_messages=True)
    # async def bans(self, ctx):
    #     """Gives a list of all the bans in the server."""

    #     bans = await ctx.guild.bans()
    #     fields = []
    #     for i in range(10):
    #         [fields.append([f"{x.user.name}#{x.user.discriminator}", f"{x.reason}"]) for x in bans]
    #     ban_list = menus.MenuPages(source=BanMenusI2(fields), delete_message_after=True, timeout=60.0, clear_reactions_after=True)
    #     await ban_list.start(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def warn(
        self, ctx: utils.CustomContext, user: discord.Member, *, reason: str = "No Reason Provided"
    ):
        """Warns a given user for a given reason, 20 warns maximum on each user."""

        user_warns = await self.bot.pool.fetch(
            "SELECT * FROM warns WHERE user_id = $1", user.id
        )

        if len(user_warns) > 20:
            return await ctx.send(
                "That user has 20 warns, please delete (at least) one to make more space."
            )

        warn_info = {
            "warn_id": str(uuid.uuid1()),
            "guild_id": ctx.guild.id,
            "warner_id": ctx.author.id,
            "user_id": user.id,
            "warn_reason": reason
            if "@" not in reason
            else reason.replace("@", "@\u200b"),
            "date_warned": int(t()),
        }

        await self.bot.pool.execute(
            "INSERT INTO warns(warn_id, guild_id, user_id, warner_id, warn_reason, date_warned) VALUES($1, $2, $3, $4, $5, $6)",
            warn_info["warn_id"],
            warn_info["guild_id"],
            warn_info["user_id"],
            warn_info["warner_id"],
            warn_info["warn_reason"],
            warn_info["date_warned"],
        )

        user_fmt = f"You were warned in **{ctx.guild.name}** by **{ctx.author}** for:\n{reason}"
        chat_fmt = f"{user.mention} was warned by {ctx.author.mention} for {reason}"
        await ctx.send(chat_fmt)

        try:
            await user.send(user_fmt)
        except discord.HTTPException:
            await ctx.send(
                f"I couldn't DM {user.mention} but they were warned anyways."
            )

        ctx.bot.dispatch("mod_cmd", ctx, "warn", ctx.author, user, reason)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def delwarn(self, ctx: utils.CustomContext, warn_id: str):
        """Deletes a given warn by its ID."""

        get_warn = await self.bot.pool.execute(
            "SELECT * FROM warns WHERE warn_id = $1 AND guild_id = $2",
            warn_id,
            ctx.guild.id,
        )

        if get_warn is None:
            return await ctx.send("That warn doesn't exist here.")

        await self.bot.pool.execute("DELETE FROM warns WHERE warn_id = $1", warn_id)
        await ctx.send(f"Successfully removed warning **{warn_id}**")

    @commands.command(aliases=["warnings"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def warns(self, ctx: utils.CustomContext, user: discord.Member):
        """Gets all of a given users warnings"""

        user_warns = await self.bot.pool.fetch(
            "SELECT * FROM warns WHERE user_id = $1 AND guild_id = $2",
            user.id,
            ctx.guild.id,
        )

        warns = []
        for row in user_warns:
            info = {
                "warn_id": row["warn_id"],
                "guild_id": row["guild_id"],
                "user_id": row["user_id"],
                "warner_id": row["warner_id"],
                "warn_reason": row["warn_reason"],
                "date_warned": row["date_warned"],
            }
            date_warned = dt.fromtimestamp(info["date_warned"])
            moderator = ctx.guild.get_member(info["warner_id"])
            warns.append(
                f"ID: **{info['warn_id']}** - Moderator: **{moderator}**\n"
                f"Warned At: **{date_warned}** - Reason:\n{info['warn_reason']}"
            )
        fmt = ["No warnings for this user."] if len(warns) == 0 else warns
        source = utils.GeneralPageSource(fmt, per_page=5)
        menu = utils.KalPages(source, clear_reactions_after=True)
        await menu.start(ctx)

    @commands.command(aliases=["unbanall"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(ban_members=True)
    async def massunban(self, ctx: utils.CustomContext):
        """Gives a prompt to unban everyone.
        Permissions needed: `Manage Server`"""

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("Are you sure you would like to unban everyone? (10 Seconds)")
        try:
            user_input = await self.bot.wait_for("message", timeout=10.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f"{ctx.author.mention} you did not reply in time.")
        else:
            user_reply = user_input.content.lower()
            if user_reply != "yes":
                return await ctx.send("Ok, backing out.")
            if user_reply == "yes":
                await ctx.send("Ok, this may take a bit.")
                bans = await ctx.guild.bans()
                for ban in bans:
                    user = ban.user
                    await ctx.guild.unban(
                        user, reason=f"Mass Unban | Responsible User: {ctx.author}"
                    )
                await ctx.send(f"Successfully unbanned {sum(1 for ban in bans)} people")

        ctx.bot.dispatch("mod_cmd", ctx, "mass unban", ctx.author, "N/A", None)

    @commands.command(aliases=["barn", "banish"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: utils.CustomContext, user: MemberOrID, *, reason: str = "No reason provided."):
        """Bans someone for a given reason.
        Permissions needed: `Ban Members`"""

        await ctx.guild.ban(user, reason=f"{reason} | Responsible User: {ctx.author}")
        await ctx.thumbsup()
        ctx.bot.dispatch("mod_cmd", ctx, "ban", ctx.author, user, reason)

    @commands.command(aliases=["unbarn", "unbanish"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: utils.CustomContext, user: BannedUser):
        """Unbans a given user.
        Permissions needed: `Ban Members`"""

        await ctx.guild.unban(
            user,
            reason=f"Responsible User: {ctx.author}",
        )
        await ctx.thumbsup()
        ctx.bot.dispatch("mod_cmd", ctx, "unban", ctx.author, user, None)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self, ctx: utils.CustomContext, user: NotStaffMember, *, reason: str = "No reason provided."
    ):
        """Kicks a user for a given reason.
        Permissions needed: `Kick Members`"""

        await user.kick(reason=f"{reason} | Responsible User: {ctx.author}")
        await ctx.thumbsup()
        ctx.bot.dispatch("mod_cmd", ctx, "kick", ctx.author, user, reason)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def setnick(self, ctx: utils.CustomContext, user: discord.Member, *, new_name: str = None):
        """Sets a new nickname for a given user.
        Permissions needed: `Manage Messages`"""

        try:
            if len(new_name) > 32:
                new_name = new_name[: len(new_name) - (len(new_name) - 32)]
            await user.edit(nick=new_name, reason=f"Responsible User: {ctx.author}")
        except discord.Forbidden:
            return await ctx.send("I was unable to change the nickname for that user.")

        await ctx.thumbsup()
        ctx.bot.dispatch("mod_cmd", ctx, "setnick", ctx.author, user, None)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def members(self, ctx: utils.CustomContext, *, role: Role):
        """Check the list of members in a certain role.
        Permissions needed: `Manage Messages`"""

        in_role = []
        [in_role.append(f"{member.mention} ({member})")
         for member in role.members]
        columns = [in_role, ["\u200b"]]
        if len(in_role) > 1:
            columns[0], columns[1] = utils.split_list(in_role)
            columns.sort(reverse=True)

        if len("\n".join(columns[0])) > 1024:
            columns[0] = columns[0][:20]

        if len("\n".join(columns[1])) > 1024:
            columns[1] = columns[1][:20]

        embed = Embed.default(
            ctx,
            title=f"Members in {role.name} [{sum(1 for m in role.members)}]"
        )
        [
            embed.add_field(
                name="\u200b", value="\n".join(column) if column else "\u200b"
            )
            for column in columns
        ]

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clean(self, ctx: utils.CustomContext):
        """Cleans all 100 previous bot messages.
        Permissions needed: `Manage Messages`"""

        await ctx.message.delete()

        def check(m):
            return m.author.bot

        await ctx.channel.purge(limit=100, check=check, bulk=True)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: utils.CustomContext, amount: int):
        """Purges a given amount of messages
        Permissions needed: `Manage Messages`"""

        await ctx.message.delete()
        await ctx.channel.purge(limit=amount)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role(self, ctx: utils.CustomContext, user: discord.Member, *roles: Role):
        """
        Give someone a role.

        Permissions needed: `Manage Roles`
        To give multiple roles, this is the syntax:
        `{prefix}role @kal#1806 "role one" role2 role`
        """

        mr_ids = [
            622258457785008150,
            668232158862639134,
            622267750232096808,
            703780954602471445,
            735699294174183454,
        ]

        modifiers = []

        current_roles = user.roles

        for role in roles:
            if role.id in mr_ids:
                continue
            if role in user.roles:
                modifiers.append(f"-{role.mention}")
                current_roles.remove(role)
            else:
                modifiers.append(f"+{role.mention}")
                current_roles.append(role)

        await user.edit(roles=current_roles)
        await ctx.thumbsup()

        embed = Embed.default(
            ctx,
            title="Updated Member Roles",
            description=f"{user.mention} | {' '.join(modifiers)}",
        )
        await ctx.send(embed=embed)

    @role.command(name="add")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_add(self, ctx: utils.CustomContext, *, role: str):
        """Adds a new role with a given name."""

        await ctx.guild.create_role(name=role, reason=f"Responsible User: {ctx.author}")
        await ctx.thumbsup()

    @role.command(name="del")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_del(self, ctx: utils.CustomContext, *, role: Role):
        """Deletes a given role."""

        await role.delete(reason=f"Responsible User: {ctx.author}")
        await ctx.thumbsup()

    @role.command(name="colour", aliases=["color"])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_colour(self, ctx: utils.CustomContext, role: Role, colour: str):
        """Sets the colour of a given role."""

        hex_regex = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"

        if not re.match(hex_regex, colour):
            return await ctx.send(
                "The colour must be a properly formed **hex** colour."
            )

        hex_to_rgb = utils.hex_to_rgb(colour[1:])
        colour = discord.Colour.from_rgb(
            hex_to_rgb[0], hex_to_rgb[1], hex_to_rgb[2])
        await role.edit(colour=colour)
        await ctx.thumbsup()

    @role.command(name="info")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    async def role_info(self, ctx: utils.CustomContext, *roles: Role):
        """Get information on a given role."""

        embed_list = []

        for role in roles:
            role_perms = []

            permissions_dict = {
                "kick_members": "Kick Members",
                "ban_members": "Ban Members",
                "administrator": "Administrator",
                "manage_channels": "Manage Channels",
                "manage_guild": "Manage Server",
                "manage_messages": "Manage Messages",
                "mention_everyone": "Mention Everyone",
                "mute_members": "Mute Members (VC)",
                "deafen_members": "Deafen Members (VC)",
                "move_members": "Move Members (VC)",
                "manage_nicknames": "Manage Nicknames",
                "manage_roles": "Manage Roles"
            }

            permissions = dict(role.permissions)

            for permission, true_false in permissions.items():
                if true_false is True:
                    if (perm := permissions_dict.get(str(permission))) is not None:
                        role_perms.append(
                            f"✅ {perm}"
                        )

            repr_permissions = '\n'.join(role_perms)

            created_at_str = f"{role.created_at.day}/{role.created_at.month}/{role.created_at.year} {role.created_at.hour}:{role.created_at.minute}:{role.created_at.second}"
            role_colour = (role.colour.r, role.colour.g, role.colour.b)
            fields = [
                ["Name", role.name, True],
                ["Mention", f"`{role.mention}`", True],
                ["Created At", created_at_str, True],
                ["Role Position", role.position, True],
                ["Hoisted", role.hoist, True],
                ["Mentionable", role.mentionable, True],
                ["Colour", utils.rgb_to_hex(role_colour), True],
                ["Members", sum(1 for member in role.members), True],
                ["Permissions",
                    f"```\n{repr_permissions or 'Nothing special.'}```", False],
            ]
            embed = Embed.default(
                ctx,
                colour=discord.Color.from_rgb(*role_colour)
            )
            [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

            embed_list.append(embed)

        if len(embed_list) > 1:
            source = utils.EmbedMenu(embed_list)
            paginator = utils.KalPages(source)
            await paginator.start(ctx)
        else:
            await ctx.send(embed=embed_list[0])

    @role.command(name="id")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def role_id(self, ctx: utils.CustomContext, *roles: Role):
        """Gets the ID of one or multiple role(s).
        e.g. {prefix}role id Developer support \"Hello World\" """

        role_names = []
        role_ids = []

        for role in roles:
            if role.id in role_ids:
                continue
            role_names.append(f"{role.mention}")
            role_ids.append(f"{role.id}")

        embed = Embed.default(ctx)
        embed.add_field(name="Names", value="\n".join(role_names))
        embed.add_field(name="IDs", value="\n".join(role_ids))
        await ctx.send(embed=embed)

    @role.command(name="name")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_name(self, ctx: utils.CustomContext, role: Role, *, name: str):
        """Changes the name of a given role.
        E.g. {prefix}role name \"Role Name\" New Role Name Here"""

        await role.edit(name=name)
        await ctx.thumbsup()


def setup(bot):
    bot.add_cog(Moderation(bot, show_name="⚔ Moderation"))
