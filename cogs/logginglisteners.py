import discord
import utils
import textwrap
import typing as t
from discord.ext import commands
from discord import abc


class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot: utils.MyBot = bot

    async def do_logging(self, guild: discord.Guild, fields: list, **kwargs):
        if self.bot.config[guild.id]["log_channel"] is None:
            return

        title = kwargs.pop("title")
        thumbnail = kwargs.pop("thumbnail", None)

        embed = self.bot.embed(title=title)
        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

        _id = self.bot.config[guild.id]["log_channel"]
        await self.bot.get_channel(_id).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        pass
        # created_at = utils.format_time(member.created_at)
        # created_at_fmt = f'{created_at["date"]} ({created_at["precise"]})'

        # fields = [
        #     ["Member Name", member.name, False],
        #     ["Member Created at", created_at_fmt, False],
        #     ["Member Mention", f'`{member.mention}`', False],
        #     ["Member ID", f'{member.id}', False],
        # ]

        # thumbnail_url = str(member.avatar_url)
        # await self.do_logging(
        #     member.guild,
        #     fields,
        #     thumbnail=thumbnail_url,
        #     title="Member Joined."
        # )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pass
        # created_at = utils.format_time(member.created_at)
        # joined_at = utils.format_time(member.joined_at)
        # created_at_fmt = f'{created_at["date"]} ({created_at["precise"]})'
        # joined_at_fmt = f'{joined_at["date"]} ({joined_at["precise"]})'

        # fields = [
        #     ["Member Name", member.name, False],
        #     ["Member Created at", created_at_fmt, False],
        #     ["Member Joined at", joined_at_fmt, False],
        #     ["Member Mention", f'`{member.mention}`', False],
        #     ["Member ID", f'{member.id}', False],
        # ]

        # thumbnail_url = str(member.avatar_url)
        # await self.do_logging(
        #     member.guild,
        #     fields,
        #     thumbnail=thumbnail_url,
        #     title="Member Removed."
        # )


def setup(bot):
    bot.add_cog(Listeners(bot))
