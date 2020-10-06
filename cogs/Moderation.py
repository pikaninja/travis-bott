from discord.ext import commands, tasks, menus

from utils import utils, db

from time import time as t

from datetime import datetime as dt, timedelta

import asyncio
import discord
import typing
import uuid
import re

def can_execute_action(ctx, user, target):
    return user.id == ctx.bot.owner_id or \
           user == ctx.guild.owner or \
           user.top_role > target.top_role

class MemberNotFound(Exception):
    pass

async def resolve_member(guild, member_id):
    member = guild.get_member(member_id)
    if member is None:
        if guild.chunked:
            raise MemberNotFound()
        try:
            member = await guild.fetch_member(member_id)
        except discord.NotFound:
            raise MemberNotFound() from None
    return member

class MemberID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
                m = await resolve_member(ctx.guild, member_id)
            except ValueError:
                raise commands.BadArgument(f"{argument} is not a valid member or member ID.") from None
            except MemberNotFound:
                # hackban case
                return type('_Hackban', (), {'id': member_id, '__str__': lambda s: f'Member ID {s.id}'})()

        if not can_execute_action(ctx, ctx.author, m):
            raise commands.BadArgument('You cannot do this action on this user due to role hierarchy.')
        return m

# class BanMenu(menus.Menu):
#     def __init__(self, *, fields=None, timeout=180.0, delete_message_after=False, clear_reactions_after=True, check_embeds=False, message=None):
#         self.fields = fields
#         self.page = 0
#         self.msg = []
#         super().__init__(timeout=timeout, delete_message_after=delete_message_after, clear_reactions_after=clear_reactions_after, check_embeds=check_embeds, message=message)

#     async def send_initial_message(self, ctx, channel):
#         embed = utils.embed_message(title="All Bans")
#         [embed.add_field(name=n, value=v, inline=False) for n, v in self.fields]
#         self.msg = await channel.send(embed=embed)
#         return self.msg

#     @menus.button("👈")
#     async def on_back_page(self, payload):
#         self.page -= 1

#     @menus.button("👉")
#     async def on_forward_page(self, payload):
#         self.page += 1

#     @menus.button('\N{CROSS MARK}')
#     async def on_stop_press(self, payload):
#         self.page = 0
#         self.stop()

class BanMenusI2(menus.ListPageSource):
    def __init__(self, data):
        self.data = data
        super().__init__(data, per_page=4)

    async def format_page(self, menu, page):
        embed = utils.embed_message(title="All Bans")
        [embed.add_field(name=n, value=v, inline=False) for n, v in self.data]
        return embed

class Moderation(commands.Cog, name="⚔ Moderation"):
    """Moderation Commands"""
    def __init__(self, bot):
        self.bot = bot
        self.check_mutes.start()
    
    @tasks.loop(seconds=30)
    async def check_mutes(self):
        await self.bot.wait_until_ready()
        mutes = await db.records("SELECT * FROM guild_mutes")
        for record in mutes:
            ends_at = record[2]
            ends_in = int(ends_at - t())
            guild = self.bot.get_guild(record[0])
            member = guild.get_member(record[1])
            mute_role_id = await db.field("SELECT mute_role_id FROM guild_settings WHERE guild_id = ?", guild.id)
            if ends_in <= 0:
                await db.execute("DELETE FROM guild_mutes WHERE member_id = ? AND guild_id = ?",
                                 member.id, guild.id)
                await db.commit()
                await member.remove_roles(guild.get_role(mute_role_id))
            else:
                pass

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
    async def warn(self, ctx, user: discord.Member, *, reason: str = "No Reason Provided"):
        """Warns a given user for a given reason, 20 warns maximum on each user."""

        user_warns = await db.records("SELECT * FROM warns WHERE user_id = ?", user.id)

        if len(user_warns) > 20:
            return await ctx.send("That user has 20 warns, please delete (at least) one to make more space.")

        warn_info = {
            "warn_id": str(uuid.uuid1()),
            "guild_id": ctx.guild.id,
            "warner_id": ctx.author.id,
            "user_id": user.id,
            "warn_reason": reason if "@" not in reason else reason.replace("@", "@\u200b"),
            "date_warned": int(t())
        }

        await db.execute("INSERT INTO warns(warn_id, guild_id, user_id, warner_id, warn_reason, date_warned) VALUES(?, ?, ?, ?, ?, ?)",
            warn_info["warn_id"],
            warn_info["guild_id"],
            warn_info["user_id"],
            warn_info["warner_id"],
            warn_info["warn_reason"],
            warn_info["date_warned"])
        await db.commit()

        user_fmt = f"You were warned in **{ctx.guild.name}** by **{ctx.author}** for:\n{reason}"
        chat_fmt = f"{user.mention} was warned by {ctx.author.mention} for {reason}"
        await ctx.send(chat_fmt)
        await user.send(user_fmt)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def delwarn(self, ctx, warn_id: str):
        """Deletes a given warn by its ID."""

        get_warn = await db.record("SELECT * FROM warns WHERE warn_id = ? AND guild_id = ?", warn_id, ctx.guild.id)

        if get_warn is None:
            return await ctx.send("That warn doesn't exist here.")
        
        await db.execute("DELETE FROM warns WHERE warn_id = ?", warn_id)
        await db.commit()
        await ctx.send(f"Successfully removed warning **{warn_id}**")

    @commands.command(aliases=["warnings"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def warns(self, ctx, user: discord.Member):
        """Gets all of a given users warnings"""
        
        user_warns = await db.records("SELECT * FROM warns WHERE user_id = ? AND guild_id = ?", user.id, ctx.guild.id)
        embed = utils.embed_message(title=f"Warns for {user}")
        fmt = ""
        warns = []
        for row in user_warns:
            info = {
                "warn_id": row[0],
                "guild_id": row[1],
                "user_id": row[2],
                "warner_id": row[3],
                "warn_reason": row[4],
                "date_warned": row[5]
            }
            date_warned = dt.fromtimestamp(info["date_warned"])
            moderator = ctx.guild.get_member(info['warner_id'])
            warns.append(f"ID: **{info['warn_id']}** - Moderator: **{moderator}**\nWarned At: **{date_warned}** - Reason:\n{info['warn_reason']}")
        fmt = "No warnings for this user." if len(warns) == 0 else "\n".join(warns)
        embed.description = fmt
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def moderations(self, ctx):
        """Gives a list of all of the active mutes."""

        moderations = []
        mutes = await db.records("SELECT * FROM guild_mutes WHERE guild_id = ?", ctx.guild.id)
        for record in mutes:
            ends_at = record[2]
            ends_in = int(ends_at - t())
            member = ctx.guild.get_member(record[1])
            if member is None:
                member.append(f"❌ Invalid User | {ends_in} Seconds")
            else:
                moderations.append(f"❌ {member} | {ends_in} Seconds")
            
        if not moderations:
            moderations.append("There are no active moderations.")
        
        embed = utils.embed_message(title="Active Moderations.",
                                    message="\n".join(moderations))
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, user: discord.Member, time: str, *, reason: str = "No reason provided."):
        """Mutes someone for a given amount of time.
        Permissions needed: `Manage Messages`
        Example: `mute @kal#1806 5m Way too cool for me`"""

        mute_role_id = await db.field("SELECT mute_role_id FROM guild_settings WHERE guild_id = ?", ctx.guild.id)
        check_if_muted = await db.field("SELECT member_id FROM guild_mutes WHERE guild_id = ? AND member_id = ?",
                                        ctx.guild.id, user.id)

        role = ctx.guild.get_role(mute_role_id)

        if check_if_muted:
            return await ctx.send("❌ That user is already muted.")

        check_if_staff = await utils.is_target_staff(ctx, user)

        if check_if_staff:
            return await ctx.send("🤔 That user is a staff member hmmm")

        if not role:
            role = discord.utils.get(ctx.guild.roles, "Muted")
            if not role:
                return await ctx.send("I was unable to find any role to mute with.")

        if not time.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9")) and \
            not time.endswith(("s", "m", "h")):
            return await ctx.send("Time must be done in the format of [Amount of Unit][Unit (s, m, h)]")

        raw_time = int(time[:-1])
        if time.endswith("s"):
            await db.execute("INSERT INTO guild_mutes(guild_id, member_id, end_time) VALUES(?, ?, ?)",
                             ctx.guild.id, user.id, int(t() + raw_time))
        elif time.endswith("m"):
            await db.execute("INSERT INTO guild_mutes(guild_id, member_id, end_time) VALUES(?, ?, ?)",
                             ctx.guild.id, user.id, int(t() + (raw_time * 60)))
        elif time.endswith("h"):
            await db.execute("INSERT INTO guild_mutes(guild_id, member_id, end_time) VALUES(?, ?, ?)",
                             ctx.guild.id, user.id, int(t() + ((raw_time * 60) * 60)))
        else:
            return await ctx.send("Time must be done in the format of [Amount of Unit][Unit (s, m, h)]")
        
        await db.commit()
        await user.add_roles(role, reason=f"Muted by: {ctx.author}")
        await ctx.send(f"⚔ Successfully muted {user} for {time} with the reason: {reason}")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, user: discord.Member):
        """Unmutes a given user who has the servers muted role"""

        mute_role_id = await db.field("SELECT mute_role_id FROM guild_settings WHERE guild_id = ?", ctx.guild.id)

        if mute_role_id is None:
            return await ctx.send(f"There is no mute role set for this server, please run `{ctx.prefix}muterole [Role]` to set one up.")

        role = ctx.guild.get_role(mute_role_id)

        if role in user.roles:
            await user.remove_roles(role, reason=f"Unmuted by: {ctx.author}")
            await ctx.thumbsup()
        else:
            await ctx.send("That user is not muted!")

    @commands.command(aliases=["unbanall"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(ban_members=True)
    async def massunban(self, ctx):
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
                    await ctx.guild.unban(user, reason=f"Mass Unban | Responsible User: {ctx.author}")
                await ctx.send(f"Successfully unbanned {len(bans)} people")
    
    @commands.command(aliases=["barn", "banish"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, user: MemberID, *, reason: str = "No reason provided."):
        """Bans someone for a given reason.
        Permissions needed: `Ban Members`"""

        # if not re.fullmatch('[0-9]{17,18}', user.id):
        #     if await utils.is_target_staff(ctx, user):
        #         return await ctx.send("😬 That person is staff...")
        
        await ctx.guild.ban(user, reason=f"{reason} | Responsible User: {ctx.author}")
        await ctx.thumbsup()

    @commands.command(aliases=["unbarn", "unbanish"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, user: str):
        """Unbans a given user.
        Permissions needed: `Ban Members`"""

        await ctx.guild.unban(await utils.get_user_banned(ctx.guild, user),
                              reason=f"Responsible User: {ctx.author}")
        await ctx.thumbsup()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: str = "No reason provided."):
        """Kicks a user for a given reason.
        Permissions needed: `Kick Members`"""

        if await utils.is_target_staff(ctx, user):
            return await ctx.send("😕 That user is a staff member...")
        
        await user.kick(reason=f"{reason} | Responsible User: {ctx.author}")
        await ctx.thumbsup()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def setnick(self, ctx, user: discord.Member, new_name: str = None):
        """Sets a new nickname for a given user.
        Permissions needed: `Manage Messages`"""

        try:
            if len(new_name) > 32:
                new_name = new_name[:len(new_name) - (len(new_name) - 32)]
            await user.edit(nick=new_name, reason=f"Responsible User: {ctx.author}")
        except discord.Forbidden:
            return await ctx.send("I was unable to change the nickname for that user.")
        
        await ctx.thumbsup()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def members(self, ctx, role: str):
        """Check the list of members in a certain role.
        Permissions needed: `Manage Messages`"""

        in_role = []
        role = await utils.find_roles(ctx.guild, role)
        [in_role.append(f"{member.mention} ({member})") for member in role.members]
        columns = [in_role, ["\u200b"]]
        if len(in_role) > 1:
            columns[0], columns[1] = utils.split_list(in_role)
            columns.sort(reverse=True)
        
        embed = utils.embed_message(title=f"Members in {role.name} [{len(role.members)}]")
        [embed.add_field(name="\u200b", value="\n".join(column) if column else "\u200b") for column in columns]
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clean(self, ctx):
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
    async def purge(self, ctx, amount: int):
        """Purges a given amount of messages
        Permissions needed: `Manage Messages`"""

        await ctx.message.delete()
        await ctx.channel.purge(limit=amount)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role(self, ctx, user: discord.Member, *roles: str):
        """
        Permissions needed: `Manage Roles`

        Give someone a role.
        To give multiple roles, this is the syntax:
        `{prefix}role @kal#1806 "role one" role2 role`
        """

        mr_ids = [622258457785008150,
                  668232158862639134]

        modifiers = []

        current_roles = user.roles

        for role in roles:
            role = await utils.find_roles(ctx.guild, role)
            if role.id in mr_ids:
                pass
            if role in user.roles:
                modifiers.append(f"-{role.mention}")
                current_roles.remove(role)
            else:
                modifiers.append(f"+{role.mention}")
                current_roles.append(role)
        
        await user.edit(roles=current_roles)
        await ctx.thumbsup()
        
        embed = utils.embed_message(title="Updated Member Roles",
                                    message=f"{user.mention} | {' '.join(modifiers)}")
        await ctx.send(embed=embed)

    @role.command(name="add")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_add(self, ctx, *, role: str):
        """Adds a new role with a given name."""

        await ctx.guild.create_role(name=role, reason=f"Responsible User: {ctx.author}")
        await ctx.thumbsup()

    @role.command(name="del")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_del(self, ctx, *, role: str):
        """Deletes a given role."""

        role = await utils.find_roles(ctx.guild, role)
        await role.delete(reason=f"Responsible User: {ctx.author}")
        await ctx.thumbsup()

    @role.command(name="colour", aliases=["color"])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_colour(self, ctx, role: str, colour: str):
        """Sets the colour of a given role."""

        role = await utils.find_roles(ctx.guild, role)
        hex_regex = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"

        if not re.match(hex_regex, colour):
            return await ctx.send("The colour must be a properly formed **hex** colour.")

        hex_to_rgb = utils.hex_to_rgb(colour[1:])
        colour = discord.Colour.from_rgb(hex_to_rgb[0], hex_to_rgb[1], hex_to_rgb[2])
        await role.edit(colour=colour)
        await ctx.thumbsup()

    @role.command(name="info")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    async def role_info(self, ctx, role: str):
        """Get information on a given role."""

        role = await utils.find_roles(ctx.guild, role)
        created_at_str = f"{role.created_at.day}/{role.created_at.month}/{role.created_at.year} {role.created_at.hour}:{role.created_at.minute}:{role.created_at.second}"
        role_colour = (role.colour.r, role.colour.g, role.colour.b)
        fields = [
            ["Name", role.name],
            ["Mention", f"`{role.mention}`"],
            ["Created At", created_at_str],
            ["Role Position", role.position],
            ["Hoisted", role.hoist],
            ["Mentionable", role.mentionable],
            ["Colour", utils.rgb_to_hex(role_colour)],
            ["Members", len(role.members)],
            ["Permissions", utils.check_role_permissions(ctx, role)]
        ]
        embed = utils.embed_message(colour=discord.Color.from_rgb(role_colour[0], role_colour[1], role_colour[2]))
        [embed.add_field(name=n, value=v) for n, v in fields]
        await ctx.send(embed=embed)

    @role.command(name="id")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def role_id(self, ctx, *role: str):
        """Gets the ID of one or multiple role(s).
        e.g. {prefix}role id Developer support \"Hello World\""""

        role_names = []
        role_ids = []

        for r in role:
            _role = await utils.find_roles(ctx.guild, r)
            if _role.id in role_ids:
                return
            role_names.append(f"{_role.mention}")
            role_ids.append(f"{_role.id}")

        embed = utils.embed_message()
        embed.add_field(name="Names", value="\n".join(role_names))
        embed.add_field(name="IDs", value="\n".join(role_ids))
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Moderation(bot))
