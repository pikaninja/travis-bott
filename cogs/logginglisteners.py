import discord
import utils
import typing as t
from discord.ext import commands
from discord import abc


class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot: utils.MyBot = bot

    def get_log_channel(self, guild: discord.Guild) -> t.Optional[discord.TextChannel]:
        logging_channel = self.bot.config[guild.id]['log_channel']

        if logging_channel:
            logging_channel = self.bot.get_channel(logging_channel)

        return logging_channel

    @commands.Cog.listener('on_guild_channel_create')
    async def log_channel_create(self, channel: abc.GuildChannel):
        """This event gets fired whenever a channel is created.
        This could be any type of channel (Text, Voice etc.)"""

        log_channel = self.get_log_channel(channel.guild)

        if not log_channel:
            return

        created_at = utils.format_time(channel.created_at)
        created_at_fmt = f'{created_at["date"]} ({created_at["precise"]})'

        fields = [
            ['Channel Name', channel.name, False],
            ['Channel Category', channel.category, False],
            ['Channel Created At', created_at_fmt, False],
        ]

        embed = self.bot.embed(title='Channel Created.')
        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

        await log_channel.send(embed=embed)

    @commands.Cog.listener('on_guild_channel_delete')
    async def log_channel_delete(self, channel: abc.GuildChannel):
        """This event gets fired whenever a channel is deleted.
        This could be any type of channel (Text, Voice etc.)"""

        log_channel = self.get_log_channel(channel.guild)

        if not log_channel:
            return

        created_at = utils.format_time(channel.created_at)
        created_at_fmt = f'{created_at["date"]} ({created_at["precise"]})'

        fields = [
            ['Channel Name', channel.name, False],
            ['Channel Category', channel.category, False],
            ['Channel Created At', created_at_fmt, False],
        ]

        embed = self.bot.embed(title='Channel Deleted.')
        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

        await log_channel.send(embed=embed)

    @commands.Cog.listener('on_member_join')
    async def log_members_joined(self, member: discord.Member):
        """This event gets fired whenever a member joins a server."""

        log_channel = self.get_log_channel(member.guild)

        if not log_channel:
            return

        created_at = utils.format_time(member.created_at)
        created_at_fmt = f'{created_at["date"]} ({created_at["precise"]})'

        fields = [
            ['Member Name', member.name, False],
            ['Member Created at', created_at_fmt, False],
            ['Member Mention', f'`{member.mention}`', False],
        ]

        embed = self.bot.embed(title='New Member Joined.')
        embed.set_footer(text=f'This member\'s ID is {member.id}')
        embed.set_thumbnail(url=str(member.avatar_url))
        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

        await log_channel.send(embed=embed)

    @commands.Cog.listener('on_member_remove')
    async def log_members_joined(self, member: discord.Member):
        """This event gets fired whenever a member gets removed from a server."""

        log_channel = self.get_log_channel(member.guild)

        if not log_channel:
            return

        created_at = utils.format_time(member.created_at)
        created_at_fmt = f'{created_at["date"]} ({created_at["precise"]})'

        joined_at = utils.format_time(member.joined_at)
        joined_at_fmt = f'{joined_at["date"]} ({joined_at["precise"]})'

        fields = [
            ['Member Name', member.name, False],
            ['Member Created at', created_at_fmt, False],
            ['Member Joined at', joined_at_fmt, False],
            ['Member Mention', f'`{member.mention}`', False],
        ]

        embed = self.bot.embed(title='Member left the server.')
        embed.set_footer(text=f'This member\'s ID is {member.id}')
        embed.set_thumbnail(url=str(member.avatar_url))
        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]

        await log_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Listeners(bot))
