"""
Utilities to provide useful functions and such to the program.
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

import asyncio
import datetime
import random
import re
import time
import typing

import Levenshtein
import dateparser
import humanize

import asyncpg
import discord
import pytz
from discord import Embed
from discord.ext import commands

from .customcontext import CustomContext

UserObject = typing.Union[discord.Member, discord.User]
UserSnowflake = typing.Union[UserObject, discord.Object]


METHODS = {
    str.islower: str.lower,
    str.istitle: str.title,
    str.isupper: str.upper
}
OWO_REPL = {
    r"\By": "wy",
    r"l": "w",
    r"er": "ew",
    r"row": "rowo",
    r"rus": "ruwus",
    r"the": "thuwu",
    r"thi": "di"
}


def _maintain_case_replace(sub: str, repl: str, text: str):
    def _repl(match: re.Match):
        group = match.group()

        for cond, method in METHODS.items():
            if cond(group):
                return method(repl)
        return repl
    return re.sub(sub, _repl, text, flags=re.I)


def owoify_text(text: str):
    for sub, repl in OWO_REPL.items():
        text = _maintain_case_replace(sub, repl, text)

    return text + " " + random.choice(("owo", "uwu"))


def owoify_embed(embed: discord.Embed):
    embed.title = owoify_text(embed.title) if embed.title else None
    embed.description = (owoify_text(embed.description)
                         if embed.description else None)
    embed.set_footer(text=owoify_text(embed.footer.text),
                     icon_url=embed.footer.icon_url) if embed.footer else None
    embed.set_author(name=owoify_text(embed.author.name),
                     url=embed.author.url,
                     icon_url=embed.author.icon_url) if embed.author else None
    for i, field in enumerate(embed.fields):
        embed.set_field_at(
            i,
            name=owoify_text(field.name),
            value=owoify_text(field.value),
            inline=field.inline
        )
    return embed


def codeblock(content: str, language: str="py"):
    return f"```{language}\n{content}```"


class TimeConverter(commands.Converter):
    async def convert(self, ctx: CustomContext, argument: str):
        DAY_REGEX = re.compile(r"^(?i)(\d){1,3}d$")
        MONTH_REGEX = re.compile(r"^(?i)(\d){1,3}mo$")
        YEAR_REGEX = re.compile(r"^(?i)(\d){1,3}y$")

        if DAY_REGEX.match(argument):
            argument = argument.strip("d")
            parsed = dateparser.parse(f"in {argument} days")

            if not parsed:
                raise commands.BadArgument("I couldn't resolve that given time.")

            if parsed < datetime.datetime.utcnow():
                raise commands.BadArgument("I couldn't resolve that given time.")

            return parsed

        elif MONTH_REGEX.match(argument):
            argument = argument.strip("mo")
            parsed = dateparser.parse(f"in {argument} months")

            if not parsed:
                raise commands.BadArgument("I couldn't resolve that given time.")

            if parsed < datetime.datetime.utcnow():
                raise commands.BadArgument("I couldn't resolve that given time.")

            return parsed

        elif YEAR_REGEX.match(argument):
            argument = argument.strip("y")
            parsed = dateparser.parse(f"in {argument} years")

            if not parsed:
                raise commands.BadArgument("I couldn't resolve that given time.")

            if parsed < datetime.datetime.utcnow():
                raise commands.BadArgument("I couldn't resolve that given time.")

            return parsed

        argument = argument if argument.startswith("in ") else f"in {argument}"
        parsed = dateparser.parse(argument)

        if not parsed:
            raise commands.BadArgument("I couldn't resolve that given time.")

        return parsed


class RoleConverter(commands.Converter):
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


def has_voted():
    async def predicate(ctx: CustomContext):
        hdrs = {"Authorization": ctx.bot.api_key_for("top_gg_api")}
        url = f"https://top.gg/api/bots/706530005169209386/check?userId={ctx.author.id}"

        async with ctx.bot.session.get(url, headers=hdrs) as response:
            data = await response.json()
            has_user_voted = bool(data["voted"])

        if not has_user_voted:
            raise UserNotVoted(
                "[Vote for the bot here to use this command.](https://top.gg/bot/706530005169209386/vote)")

        return True

    return commands.check(predicate=predicate)


class UserNotVoted(commands.CheckFailure):
    pass


class MemberIsStaff(commands.CheckFailure):
    pass


class NoTodoItems(commands.CheckFailure):
    pass


class NotTagOwner(commands.CheckFailure):
    pass


async def set_giveaway(bot, end_time, channel_id, message_id):
    async def giveaway_task(bot, end_time, channel_id, message_id):
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        seconds_until = (end_time - now).total_seconds()
        await asyncio.sleep(seconds_until)

        try:
            await bot.pool.execute("DELETE FROM giveaways WHERE message_id = $1",
                                   message_id)
            channel = await bot.fetch_channel(channel_id)
            message = discord.PartialMessage(channel=channel, id=message_id)
            bot.dispatch("giveaway_end", message)
        except asyncpg.PostgresError:
            pass

    bot.loop.create_task(giveaway_task(bot, end_time, channel_id, message_id))


async def set_mute(bot, guild_id, user_id, _time):
    async def mute_task(bot, guild_id, user_id, _time):
        await asyncio.sleep(_time)

        try:
            await bot.pool.execute("DELETE FROM guild_mutes WHERE member_id = $1 AND guild_id = $2",
                                   user_id, guild_id)
            guild = await bot.fetch_guild(guild_id)
            member = await guild.fetch_member(user_id)
            mute_role = guild.get_role(bot.config[guild_id]["mute_role_id"])

            await member.remove_roles(mute_role, reason="Mute time is over.")
        except asyncpg.PostgresError:
            pass

    bot.loop.create_task(mute_task(bot, guild_id, user_id, _time))


def log(*args):
    print(f"{time.strftime('%I:%M:%S')} | {' '.join(map(str, args))}")


async def is_target_staff(ctx, user) -> str:
    ch = ctx.message.channel
    permissions = ch.permissions_for(user).manage_messages
    return permissions


async def get_user_banned(guild, name_arg):
    banned_users = await guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if name_arg.lower().startswith(user.name.lower()):
            member_to_unban = discord.Object(id=user.id)
            return member_to_unban
    return None


async def find_roles(guild, role_arg) -> discord.Role:
    if re.fullmatch("<@&[0-9]{15,}>", role_arg) is not None:
        return guild.get_role(int(role_arg[3:-1]))
    if role_arg.isnumeric():
        if re.fullmatch("[0-9]{15,}", role_arg) is not None:
            return guild.get_role(int(role_arg))
    for role in guild.roles:
        if role.name.lower().startswith(role_arg.lower()):
            return role
    return None


def hex_to_rgb(h) -> tuple:
    return tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#%02x%02x%02x" % rgb


def get_activity(ctx, m: discord.Member):
    """Gets the users current activity:
    Purpose: Get their whole activity if they're using Spotify or just playing a game, watching something or whatever else."""

    if isinstance(m.activities, discord.Spotify):
        info = [
            f"{', '.join(m.activities.artists)} - {m.activities.title}",
            f"Album: {m.activities.album}",
            f"Duration: {m.activities.duration}" f"{m.activities.track_id}",
        ]
        return info
    elif isinstance(m.activities, discord.BaseActivity):
        return [m.activities]


def check_permissions(ctx, m: discord.Member):
    if m.id == ctx.guild.owner_id:
        return "Server Owner"
    elif m.permissions_in(ctx.channel).administrator:
        return "Server Admin"
    elif m.permissions_in(ctx.channel).manage_guild:
        return "Server Manager"
    elif m.permissions_in(ctx.channel).manage_messages:
        return "Server Moderator"
    else:
        return "No special permissions"


def check_role_permissions(ctx, role: discord.Role):
    if role.permissions.administrator:
        return "Administrator"
    elif role.permissions.manage_guild:
        return "Manager"
    elif role.permissions.manage_messages:
        return "Moderator"
    elif role.permissions.mute_members:
        return "Voice Moderator"
    else:
        return "No special permissions"


def split_list(a_list) -> typing.Tuple[typing.Any, typing.Any]:
    half = len(a_list) // 2
    return a_list[:half], a_list[half:]


def embed_message(
    *,
    title: str = None,
    message: str = None,
    colour: discord.Colour = 0xE0651D,
    footer_text: str = "",
    footer_icon: str = "",
    url: str = None,
    thumbnail: str = "",
    timestamp: datetime.datetime = Embed.Empty,
) -> Embed:
    """
    Purpose
    -------
    Returns a basic embed with a given title,
    message which is the description and colour if one is set.
    :rtype: object
    """
    new_embed = Embed(
        title=title, description=message, colour=colour, url=url, timestamp=timestamp
    )
    new_embed.set_footer(text=footer_text, icon_url=footer_icon)
    new_embed.set_thumbnail(url=thumbnail)
    return new_embed


def extract_id(argument: str, strict: bool = True):
    """Extract id from argument."""
    """
    Parameters
    ----------
    argument: str
        text to parse

    Returns
    ----------
    str
        the bare id
    """
    ex = "".join(list(filter(str.isdigit, str(argument))))
    if len(ex) < 15 and strict:
        return None
    return ex


class MemberID(commands.Converter):
    """Extract a member id and force to be in guild."""

    """
    The main purpose is for banning people and forcing
    the to-be-banned user in the guild.
    """

    async def convert(self, ctx, argument):
        """Discord converter."""
        try:
            argument = extract_id(argument)
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                return str(int(argument, base=10))
            except ValueError:
                raise commands.BadArgument(
                    f"{argument} is not a valid'\
                                            'member or member ID."
                ) from None
        else:
            can_execute = (
                ctx.author.id == ctx.bot.owner_id
                or ctx.author == ctx.guild.owner
                or ctx.author.top_role > m.top_role
            )

            if not can_execute:
                raise commands.BadArgument(
                    "You cannot do this action on this" " user due to role hierarchy."
                )
            return m


def format_time(dt):
    humanized = humanize.precisedelta(dt, suppress=["seconds"], format="%0.0f")
    return {"date": dt.strftime("%B %d %Y %I:%M:%S"), "precise": humanized}


def get_best_difference(list_of_strings, string_main) -> typing.Union[None, str]:
    differences = {}
    values = []
    for string in list_of_strings:
        difference = Levenshtein.distance(string_main, string)
        differences[string] = difference
    for key, value in differences.items():
        values.append(value)
    values = sorted(values, reverse=False)
    if values[0] > 5:
        return None
    differences = sorted(differences, key=differences.get, reverse=False)
    return differences[0]
