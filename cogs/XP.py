from discord.ext import commands
import discord

import time

from datetime import datetime as dt

from utils import db, utils
from utils.CustomContext import CustomContext
from utils import CustomBot

import random
import asyncio


def get_weekday() -> int:
    """Returns an int representating the weekday"""

    return int(str(dt.now().weekday())) + 1


def get_xp_modifier():
    get_weekday = int(str(dt.now().weekday())) + 1
    return 0.75 if get_weekday == 6 or 7 else 0.50


message_reactions = {"✅": "yes", "❌": "no"}


class XP(commands.Cog, name="⚗ XP"):
    """XP System, this is a per-user XP system and not per server."""

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.xp_modifier = get_xp_modifier()

    """
    XP Algorithm Ideas:
        
        - next_xp = int(cur_xp * 2) * 0.10

        - ```
            import random

            level = 0 # Starting level / Get from DB
            xp = 0 # Starting XP / Get from DB
            xp_required = xp + xp * 0.50 # Fixed

            xp += random.randint(10, 15)
            if xp >= xp_required:
                level += 1
                xp_required = xp + xp * 0.50
        ```

    XP Boost Ideas
        - Last week of the month
            Or
        - During the weekend

        - Big XP boost for special holidays e.g. Christmas
    """

    async def process_xp(self, ctx: CustomContext, user: discord.Member):
        """Actual function that adds xp when someone talks."""

        user_record = await db.record(
            "SELECT * FROM xp_levels WHERE user_id = ?", user.id
        )

        if user_record is None:
            await db.execute(
                "INSERT INTO xp_levels(user_id, xp, level, xp_required, xp_lock) VALUES(?, ?, ?, ?, ?)",
                user.id,
                0,
                0,
                0 + 0 * get_xp_modifier(),
                int(time.time()),
            )
            await db.commit()

        user_record = await db.record(
            "SELECT * FROM xp_levels WHERE user_id = ?", user.id
        )
        xp = user_record[1]
        level = user_record[2]
        xp_required = int(user_record[3])
        xp_lock = user_record[4]

        xp_to_add = random.randint(10, 15)

        if int(time.time()) >= xp_lock:
            await self.add_xp(user, xp_to_add)
            xp = await db.field("SELECT xp FROM xp_levels WHERE user_id = ?", user.id)
            if xp >= xp_required:
                await self.set_level(user, level + 1)
                await db.execute(
                    "UPDATE xp_levels SET xp_required = ? WHERE user_id = ?",
                    int(xp + xp * get_xp_modifier()),
                    user.id,
                )
                await db.commit()

                messages = await db.field(
                    "SELECT messages FROM xp_settings WHERE guild_id = ?", ctx.guild.id
                )
                message_channel_id = await db.field(
                    "SELECT messages_channel FROM xp_settings WHERE guild_id = ?",
                    ctx.guild.id,
                )

                if messages == "yes":
                    embed = utils.embed_message(
                        title="🎉🥳 Level Up!",
                        message=f"Congratulations to {ctx.author.mention}, they reached level {level + 1}",
                    )
                    if not message_channel_id:
                        await ctx.send(embed=embed)
                    else:
                        channel = ctx.bot.get_channel(message_channel_id)
                        await channel.send(embed=embed)

            await db.execute(
                "UPDATE xp_levels SET xp_lock = ? WHERE user_id = ?",
                int(time.time() + 60),
                user.id,
            )
            await db.commit()

    async def add_xp(self, user: discord.Member, amount: int):
        """Adds a certain amount of XP to a given user."""

        cur_xp = await db.field("SELECT xp FROM xp_levels WHERE user_id = ?", user.id)
        await db.execute(
            "UPDATE xp_levels SET xp = ? WHERE user_id = ?", cur_xp + amount, user.id
        )
        await db.commit()

    async def set_level(self, user: discord.Member, new_level: int):
        """Sets a given users level."""

        await db.execute(
            "UPDATE xp_levels SET level = ? WHERE user_id = ?", new_level, user.id
        )
        await db.commit()

    async def reset_user(self, user: discord.Member):
        """Resets a given user."""

        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        await self.process_xp(ctx, message.author)

    @commands.group(invoke_without_command=True)
    async def xp(self, ctx):
        """The commands that allow you set up the XP system."""

        await ctx.send_help(ctx.command)

    @xp.command(name="messages")
    @commands.has_permissions(manage_guild=True)
    async def xp_messages(self, ctx):
        """Enables or disables level up messages for the server."""

        await ctx.send(
            "Would you like to enable level up messages in this server? `yes` or `no`."
        )

        try:

            def check(m):
                return ctx.author == m.author and ctx.channel == m.channel

            user_input = await self.bot.wait_for("message", timeout=10.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f"You didn't respond in time! {ctx.author.mention}")
        else:
            content = user_input.content.lower()
            if content == "no":
                settings = await db.record(
                    "SELECT messages FROM xp_settings WHERE guild_id = ?", ctx.guild.id
                )
                if not settings:
                    await db.execute(
                        "INSERT INTO xp_settings(guild_id, messages) VALUES(?, ?)",
                        ctx.guild.id,
                        "no",
                    )
                    await db.commit()
                    await ctx.send(f"Successfully disabled XP messages")
                else:
                    await db.execute(
                        "UPDATE xp_settings SET messages = ? WHERE guild_id = ?",
                        "no",
                        ctx.guild.id,
                    )
                    await db.commit()
                    await ctx.send(f"Successfully disabled XP messages")
            elif content == "yes":
                settings = await db.record(
                    "SELECT messages FROM xp_settings WHERE guild_id = ?", ctx.guild.id
                )
                if not settings:
                    await db.execute(
                        "INSERT INTO xp_settings(guild_id, messages) VALUES(?, ?)",
                        ctx.guild.id,
                        "yes",
                    )
                    await db.commit()
                    await ctx.send(
                        f"Successfully enabled XP messages, if you'd like to set where they go do `{ctx.prefix}xp channel #Channel-Here`"
                    )
                else:
                    await db.execute(
                        "UPDATE xp_settings SET messages = ? WHERE guild_id = ?",
                        "yes",
                        ctx.guild.id,
                    )
                    await db.commit()
                    await ctx.send(
                        f"Successfully enabled XP messages, if you'd like to set where they go do `{ctx.prefix}xp channel #Channel-Here`"
                    )
            else:
                return await ctx.send("That was an invalid option.")

    @xp.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def xp_channel(self, ctx, channel: discord.TextChannel):
        """Allows you to set the text channel for where level ups go."""

        config = await db.record(
            "SELECT * from xp_settings WHERE guild_id = ?", ctx.guild.id
        )

        if channel is None:
            return await ctx.send(
                "You either did not supply a channel or it doesn't exist (I may not be able to see it)."
            )

        if not config:
            await db.execute(
                "INSERT INTO xp_settings(guild_id, messages_channel) VALUES(?, ?)",
                ctx.guild.id,
                channel.id,
            )
        elif config:
            await db.execute(
                "UPDATE xp_settings SET messages_channel = ? WHERE guild_id = ?",
                channel.id,
                ctx.guild.id,
            )
        await db.commit()

        await ctx.send(f"Successfully set level up messages to go to {channel.mention}")

    @commands.command()
    async def rank(self, ctx, user: discord.Member = None):
        """Gets your current rank and how much xp is required until you level up."""

        user = user or ctx.author
        user_record = await db.record(
            "SELECT * FROM xp_levels WHERE user_id = ?", user.id
        )

        if user_record is None:
            return await ctx.send("That user has no level or rank!")

        fields = [
            ["Level", user_record[2]],
            ["XP", f"{user_record[1]} / {user_record[3]}"],
        ]

        embed = utils.embed_message(
            title=f"{user}'s rank", thumbnail=user.avatar_url)

        [embed.add_field(name=n, value=v, inline=False) for n, v in fields]
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(XP(bot))
