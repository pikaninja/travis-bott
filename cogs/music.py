"""
Music commands for users to jam out to
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
import discord
from discord.ext import commands

import math
import logging
import wavelink
import async_timeout

import utils


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.context: utils.CustomContext = kwargs.get("context", None)
        if self.context:
            self.dj: discord.Member = self.context.author

        self.queue = asyncio.Queue()
        self.repeat = False

        self.waiting = False
        self.updating = False

        self.skip_votes = set()
        self.stop_votes = set()

    async def do_next(self):
        if self.is_playing or self.waiting:
            return

        self.skip_votes.clear()
        self.stop_votes.clear()

        try:
            self.waiting = True
            with async_timeout.timeout(300):
                track = await self.queue.get()
        except asyncio.TimeoutError:
            return await self.teardown()

        await self.play(track)
        self.waiting = False

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass


# noinspection PyUnresolvedReferences
class Music(commands.Cog, wavelink.WavelinkMixin, name="music"):
    """Music Commands"""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name

        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

        if not hasattr(bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=self.bot)

        self.bot.loop.create_task(self.__ainit__())
        self.bot.loop.create_task(self.start_nodes())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        if hasattr(self.bot, "wavelink"):
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        if self.bot.user.id != 706530005169209386:
            self.bot.unload_extension("cogs.music")
            return

        await self.bot.wavelink.initiate_node(host="127.0.0.1",
                                              port=2333,
                                              rest_uri="http://127.0.0.1:2333",
                                              password=self.bot.from_config("wavelink_pass"),
                                              identifier="Travis",
                                              region="europe")

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        print(f"Node {node.identifier} is ready!")

    # noinspection PyUnusedLocal
    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.do_next()

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        player: Player = self.bot.wavelink.get_player(
            member.guild.id, cls=Player)

        if not player.channel_id or not player.context:
            player.node.players.pop(member.guild.id)
            return

        channel = self.bot.get_channel(int(player.channel_id))

        if len(channel.members) == 1:
            return await player.teardown()

        if member == player.dj and after.channel is None:
            for m in channel.members:
                if m.bot:
                    continue
                else:
                    player.dj = m
                    return

        elif after.channel == channel and player.dj not in channel.members:
            player.dj = member

    async def cog_before_invoke(self, ctx: utils.CustomContext):
        player: Player = self.bot.wavelink.get_player(
            ctx.guild.id, context=ctx, cls=Player)

        if player.context:
            if player.context.channel != ctx.channel:
                return await ctx.send(
                    f"{ctx.author.mention} you must be in {player.context.channel.mention} for for this session."
                )

            if ctx.command.name == "connect" and not player.context:
                return

            if not player.channel_id:
                return

            channel = self.bot.get_channel(int(player.channel_id))
            if not channel:
                return

            if player.is_connected:
                if ctx.author not in channel.members:
                    return await ctx.send(
                        f"{ctx.author.mention} you must be in {channel.mention} to use voice commands."
                    )

    def required_members(self, ctx: utils.CustomContext):
        player: Player = self.bot.wavelink.get_player(
            ctx.guild.id, cls=Player)
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil(3 / 3.5)

        if ctx.command.name == "stop":
            if len(channel.members) == 3:
                required = 2

        return required

    def is_privileged(self, ctx: utils.CustomContext):
        player: Player = self.bot.wavelink.get_player(
            ctx.guild.id, cls=Player)

        return player.dj == ctx.author or ctx.author.guild_permissions.manage_messages

    @commands.command(name="connect")
    @commands.guild_only()
    async def connect_(self, ctx: utils.CustomContext):
        """Gets the bot to connect to your voice channel."""

        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            raise commands.CommandError(
                "You're not currently connected to a voice channel.")

        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.connect(channel.id)

    @commands.command(aliases=["p"])
    @commands.guild_only()
    async def play(self, ctx: utils.CustomContext, *, query: str):
        """Plays a given track."""

        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            await ctx.invoke(self.connect_)

        query = query.strip('<>')
        tracks = await self.bot.wavelink.get_tracks(f"ytsearch:{query}")

        if not tracks:
            return await ctx.send("Couldn't find any songs matching that query.")

        await ctx.send(f"Added `{tracks[0]}` to the queue.")
        await player.queue.put(tracks[0])

        if not player.is_playing:
            await player.do_next()

    @commands.command(aliases=["s"])
    @commands.guild_only()
    async def skip(self, ctx: utils.CustomContext):
        """Skips the current song playing."""

        player: Player = self.bot.wavelink.get_player(
            ctx.guild.id, cls=Player)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            player.skip_votes.clear()
            await player.stop()
            return await ctx.message.add_reaction("\U000023ed")

        required = self.required_members(ctx)
        player.skip_votes.add(ctx.author)

        if len(player.skip_votes) >= required:
            await ctx.send("\U000023ed")
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.send(f"{ctx.author.mention} has voted to skip the song.")

    @commands.command()
    @commands.guild_only()
    async def stop(self, ctx: utils.CustomContext):
        """Stops the music from playing entirely."""

        player: Player = self.bot.wavelink.get_player(
            ctx.guild.id, cls=Player)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.message.add_reaction("\U000023f9")
            return await player.teardown()

        required = self.required_members(ctx)
        player.stop_votes.add(ctx.author)

        if len(player.stop_votes) >= required:
            await ctx.send("\U000023f9")
            await player.teardown()
        else:
            await ctx.send(f"{ctx.author.mention} has voted to skip the song.")

    @commands.command(aliases=["q"])
    @commands.guild_only()
    async def queue(self, ctx: utils.CustomContext):
        """Displays the current songs that are queued."""

        player: Player = self.bot.wavelink.get_player(
            ctx.guild.id, cls=Player)

        if not player.is_connected:
            return

        if not player.is_playing:
            return await ctx.send("There are no more songs in the queue...")

        # noinspection PyProtectedMember
        entries = list()
        entries.append(player.current.title)
        [entries.append(track.title) for track in player.queue._queue]
        pages = utils.GeneralPageSource(entries, per_page=10)
        paginator = utils.KalPages(pages)

        await paginator.start(ctx)


def setup(bot):
    bot.add_cog(Music(bot, "\N{MUSICAL NOTE} Music"))
