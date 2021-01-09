import discord
import utils
import sys
import humanize
import psutil
from utils.embed import Embed
from discord.ext import commands
from decouple import config
from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES
from jishaku.features.baseclass import Feature
from jishaku.meta import __version__
from jishaku.flags import JISHAKU_HIDE
from jishaku.modules import package_version
from jishaku.codeblocks import codeblock_converter


class Jishaku(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    @Feature.Command(parent="jsk", name="gist")
    async def jsk_gist(self, ctx: commands.Context, *, content: codeblock_converter):
        """Puts given content into a gist for you."""

        url = f"https://api.github.com/gists"
        headers = {"Authorization": f"token {config('GITHUB_API')}"}
        params = {"scope": "gist"}
        payload = {"description": "GIST generated by Jishaku.", "public": True, "files": {
            "GIST generated by Jishaku (Custom)": {"content": content.content}}}

        async with self.bot.session.post(url, headers=headers, params=params, json=payload) as resp:
            data = await resp.json()

            if resp.status == 201:
                embed = Embed.default(ctx)
                embed.title = "Successfully uploaded!"
                embed.description = f"URL: {data['html_url']}"

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"The API returned a {resp.status} status")

    @Feature.Command(name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=True, hidden=JISHAKU_HIDE)
    async def jsk(self, ctx: commands.Context):
        """Overriden Jishaku Command."""

        summary = [
            f"Jishaku v{__version__}, discord.py `{package_version('discord.py')}`, "
            f"`Python {sys.version}` on `{sys.platform}`".replace("\n", ""),
            f"Module was loaded {humanize.naturaltime(self.load_time)}, "
            f"cog was loaded {humanize.naturaltime(self.start_time)}.",
            ""
        ]

        # detect if [procinfo] feature is installed
        if psutil:
            try:
                proc = psutil.Process()

                with proc.oneshot():
                    try:
                        mem = proc.memory_full_info()
                        summary.append(f"Using {humanize.naturalsize(mem.rss)} physical memory and "
                                       f"{humanize.naturalsize(mem.vms)} virtual memory, "
                                       f"{humanize.naturalsize(mem.uss)} of which unique to this process.")
                    except psutil.AccessDenied:
                        pass

                    try:
                        name = proc.name()
                        pid = proc.pid
                        thread_count = proc.num_threads()

                        summary.append(
                            f"Running on PID {pid} (`{name}`) with {thread_count} thread(s).")
                    except psutil.AccessDenied:
                        pass

                    summary.append("")  # blank line
            except psutil.AccessDenied:
                summary.append(
                    "psutil is installed, but this process does not have high enough access rights "
                    "to query process information."
                )
                summary.append("")  # blank line

        cache_summary = f"{len(self.bot.guilds)} guild(s) and {sum(g.member_count for g in self.bot.guilds)} user(s)"

        # Show shard settings to summary
        if isinstance(self.bot, discord.AutoShardedClient):
            summary.append(
                f"This bot is automatically sharded and can see {cache_summary}.")
        elif self.bot.shard_count:
            summary.append(
                f"This bot is manually sharded and can see {cache_summary}.")
        else:
            summary.append(
                f"This bot is not sharded and can see {cache_summary}.")

        # pylint: disable=protected-access
        if self.bot._connection.max_messages:
            message_cache = f"Message cache capped at {self.bot._connection.max_messages}"
        else:
            message_cache = "Message cache is disabled"

        if discord.version_info >= (1, 5, 0):
            presence_intent = f"presence intent is {'enabled' if self.bot.intents.presences else 'disabled'}"
            members_intent = f"members intent is {'enabled' if self.bot.intents.members else 'disabled'}"

            summary.append(
                f"{message_cache}, {presence_intent} and {members_intent}.")
        else:
            guild_subscriptions = f"guild subscriptions are {'enabled' if self.bot._connection.guild_subscriptions else 'disabled'}"

            summary.append(f"{message_cache} and {guild_subscriptions}.")

        # pylint: enable=protected-access

        # Show websocket latency in milliseconds
        summary.append(
            f"Average websocket latency: {self.bot.latency * 1000:,.2f}ms")

        with ctx.embed() as embed:
            embed.description = "\n".join(summary)
            await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Jishaku(bot=bot))
