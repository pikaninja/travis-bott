import datetime
import re
import time
import typing
from typing import Optional

import humanize
from decouple import config

import discord
from discord import Embed
from discord.ext.commands import when_mentioned_or
from discord.ext import commands

from . import db
from .CustomBot import MyBot

UserObject = typing.Union[discord.Member, discord.User]
UserSnowflake = typing.Union[UserObject, discord.Object]


def log(*args):
    print(f"{time.strftime('%I:%M:%S')} | {' '.join(map(str, args))}")


async def get_prefix(bot: MyBot, message: discord.Message):
    if message.guild is None:
        return "tb!"
    else:
        return bot.cache["prefixes"][message.guild.id]


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
