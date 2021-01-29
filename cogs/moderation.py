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

import humanize
import asyncpg
import utils
import asyncio
import logging
import discord
import uuid
import re
import typing as tp
from time import time as t
from datetime import datetime as dt
from discord.ext import commands, menus


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
        embed = menu.ctx.bot.embed(menu.ctx)
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


class WarnsPageSource(menus.ListPageSource):
    def __init__(self, data: tp.List[str], *, per_page=4):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu: menus.Menu, page: tp.List[str]):
        fmt = "\n".join(page)
        embed = menu.ctx.bot.embed(menu.ctx)
        embed.description = fmt

        return embed


# noinspection PyUnresolvedReferences,PyMissingConstructor
class Moderation(commands.Cog, name="moderation"):
    """Moderation Commands"""

    def __init__(self, bot):
        self.bot: utils.MyBot = bot
        self.show_name = "\N{CROSSED SWORDS} Moderation"

        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

    async def get_warn_by_id(self, user_id: int, index: int):
        sql = "SELECT * FROM warns WHERE offender_id = $1;"
        records = await self.bot.pool.fetch(sql, user_id)

        try:
            item = records[index - 1]
        except IndexError:
            raise commands.BadArgument(
                "That user does not have a warn with that ID.")

        return item["id"]

    @commands.Cog.listener("on_member_join")
    async def persistent_mutes(self, member: discord.Member):
        is_user_muted = await self.bot.pool.fetchrow("SELECT * FROM guild_mutes WHERE member_id = $1 AND guild_id = $2",
                                                     member.id, member.guild.id)

        if not is_user_muted:
            return

        mute_role_id = self.bot.config[member.guild.id]["guild_prefix"]
        mute_role = member.guild.get_role(role_id=mute_role_id)
        await member.add_roles(mute_role, reason="Mute Role Persist")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: utils.CustomContext, user: discord.Member, *, reason: str = "No Reason Provided."):
        """Warns a given user for a given reason.
        You can do `{prefix}warns someone#1234` to view their current warns."""

        if len(reason) > 255:
            raise commands.BadArgument(
                "The warn reason must not be greater than 255 characters.")

        sql = "INSERT INTO warns VALUES(default, $1, $2, $3, $4, $5);"
        values = (ctx.guild.id, ctx.author.id, user.id, reason, dt.utcnow())
        await self.bot.pool.execute(sql, *values)

        await ctx.send(
            f"Successfully warned `{user}` for: {reason}. "
            f"Do `{ctx.prefix}warns {user}` to view their current warns."
        )

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def warns(self, ctx: utils.CustomContext, *, user: discord.Member):
        """Get the current warns of a given user."""

        sql = "SELECT * FROM warns WHERE offender_id = $1;"
        records = await self.bot.pool.fetch(sql, user.id)
        ret = []

        for index, record in enumerate(records, start=1):
            warner = self.bot.get_user(record["moderator_id"])
            warned_at = record["time_warned"]
            warned_date = utils.format_time(warned_at)["date"]
            ret.append(
                f"`{index}` - Warned by: {warner} - Warned at: {warned_date} | {record['reason']}"
            )

        if not ret:
            raise commands.BadArgument("That user has no warns to display.")

        source = WarnsPageSource(ret)
        page = utils.KalPages(source)
        await page.start(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def delwarn(self, ctx: utils.CustomContext, user: discord.Member, warn_id: int):
        """Deletes a warn off a given user."""

        warn_id = await self.get_warn_by_id(user.id, warn_id)

        sql = "DELETE FROM warns WHERE id = $1;"
        await self.bot.pool.execute(sql, warn_id)
        await ctx.send(f"Successfully cleared that warn for `{user}`")

    @commands.command(aliases=["tban"], disabled=True, hidden=True)
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
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

        embed = self.bot.embed(ctx)
        embed.description = (
            f"{ctx.author.mention} ({ctx.author}) has muted {user.mention} ({user}) for {humanized} for the reason: "
            f"{reason}"
        )

        await ctx.send(embed=embed)

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
        embed = self.bot.embed(ctx)
        embed.description = f"{ctx.author.mention} ({ctx.author}) unmuted {user.mention} ({user})"

        await ctx.send(embed=embed)

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

    @commands.command(aliases=["barn", "banish"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: utils.CustomContext, user: MemberOrID, *, reason: str = "No reason provided."):
        """Bans someone for a given reason.
        Permissions needed: `Ban Members`"""

        await ctx.guild.ban(user, reason=f"{reason} | Responsible User: {ctx.author}")
        await ctx.thumbsup()

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

        embed = self.bot.embed(
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

        embed = self.bot.embed(
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
            embed = self.bot.embed(
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

        embed = self.bot.embed(ctx)
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
    bot.add_cog(Moderation(bot))
