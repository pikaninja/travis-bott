"""
Utility and general commands for users to use.
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

import argparse
import logging
import os
import re

import utils
import cse
import contextlib
import psutil
import discord
import typing
import numexpr
import humanize
from jishaku.codeblocks import codeblock_converter
from contextlib import asynccontextmanager
from discord.ext import commands, menus
from PIL import ImageColor
from currency_converter import CurrencyConverter


status_icons = {
    "online": "<:online:748253316693098609>",
    "dnd": "<:dnd:748253316777115659>",
    "idle": "<:away:748253316882104390>",
    "offline": "<:offline:748253316533846179>",
}


class AllConverter(commands.Converter):
    async def convert(self, ctx: utils.CustomContext, argument: str):

        converters = {
            commands.TextChannelConverter(): "Text Channel",
            commands.VoiceChannelConverter(): "Voice Channel",
            commands.MemberConverter(): "Server Member",
            commands.UserConverter(): "Discord User",
            commands.PartialEmojiConverter(): "Emoji",
            utils.RoleConverter(): "Server Role",
        }

        for converter, title in converters.items():
            try:
                convert = await converter.convert(ctx, argument)
                return convert.id, title
            except Exception as e:
                continue

        raise commands.BadArgument("Couldn't find anything that matches that.")


class ColourConverter(commands.Converter):
    async def convert(self, ctx: utils.CustomContext, argument: str):
        with contextlib.suppress(AttributeError):
            RGB_REGEX = re.compile(r"\(?(\d+),?\s*(\d+),?\s*(\d+)\)?")
            match = RGB_REGEX.match(argument)
            check = all(0 <= int(x) <= 255 for x in match.groups())

        if match and check:
            rgb = [int(x) for x in match.groups()]
            return discord.Colour.from_rgb(*rgb)

        converter = commands.ColourConverter()

        try:
            result = await converter.convert(ctx, argument)
        except commands.BadColourArgument:
            try:
                colour = ImageColor.getrgb(argument)
                result = discord.Colour.from_rgb(*colour)
            except ValueError:
                result = None

        if result:
            return result

        raise commands.BadArgument(
            f"Couldn't find a colour value matching `{argument}`.")


class Meta(utils.BaseCog, name="meta"):
    """General and utility commands"""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name
        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

        self.weather_api_key = self.bot.settings["keys"]["weather_api"]

    @asynccontextmanager
    async def google_search(self, query: str):
        """Context Manager to search for the CSE"""

        with contextlib.suppress(KeyError):
            keys = [self.bot.settings["keys"]["google_cse"],
                    self.bot.settings["keys"]["second_google_cse"]]
            results = []
            try:
                engine = cse.Search(keys[0])
                results = await engine.search(query, safe_search=True, max_results=10)
            except cse.QuotaExceededError:
                engine = cse.Search(keys[1])
                results = await engine.search(query, safe_search=True, max_results=10)
            finally:
                await engine.close()
                yield results

    def _get_top_coloured_role(self, target: discord.Member):
        """Helper method to get the users top role that has colour else no colour."""

        roles = target.roles
        roles.reverse()

        for role in roles:
            if role.colour != discord.Colour(0):
                return role.colour

        return discord.Colour(0)

    async def _get_task_by_enumeration(self, user: discord.Member, enumerated_id: int):
        """Helper method to get a task by its enumeration ID."""

        sql = "SELECT * FROM todos WHERE user_id = $1"
        all_tasks = await self.bot.pool.fetch(sql, user.id)

        try:
            resultant_task = all_tasks[enumerated_id - 1]
        except IndexError:
            raise commands.BadArgument(
                "You do not have a task that corresponds with that ID.")

        return resultant_task["id"]

    @commands.command(name="run")
    async def _run(self, ctx: utils.CustomContext, *, code: codeblock_converter):
        """Runs a given piece of code.
        Use the given syntax modifier in the codeblock to determine the language."""

        short_hand = {
            "py": "python",
            "c++": "cpp",
            "ts": "typescript",
            "js": "javascript",
        }

        if not hasattr(code, "language"):
            raise commands.BadArgument(
                "You must provide a codeblock with a certain language.")

        lang = code.language.lower()

        if (new_lang := short_hand.get(lang, None)):
            lang = new_lang

        content = code.content
        url = "https://emkc.org/api/v1/piston/execute"

        if lang.lower() == "java":
            lines = content.splitlines()
            base = [
                "public class temp extends Object {public static void main(String[] args) {"]
            for line in lines:
                base.append(line)
            base.append("}}")

            content = "\n".join(base)

        data = {
            "language": lang,
            "source": content,
            "args": [],
        }

        async with ctx.timeit:
            async with ctx.typing():
                async with self.bot.session.post(url, json=data) as res:
                    res_data = await res.json()
                    if res.status != 200:
                        return await ctx.send(f"{res.status} - {res_data['message']}")

                    with ctx.embed() as embed:
                        if (stdout := res_data["stdout"]):
                            if len(stdout) > 1500:
                                bin_link = await utils.mystbin(
                                    self.bot.session,
                                    stdout
                                )

                                value = f"Result too long... {bin_link}.{lang}"
                            else:
                                value = utils.codeblock(stdout, lang)

                            embed.add_field(
                                name="Stdout",
                                value=value
                            )

                        if (stderr := res_data["stderr"]):
                            if len(stderr) > 1500:
                                bin_link = await utils.mystbin(
                                    self.bot.session,
                                    stderr
                                )

                                value = f"Result too long... {bin_link}.{lang}"
                            else:
                                value = utils.codeblock(stderr, lang)

                            embed.add_field(
                                name="Stderr",
                                value=value
                            )

                        await ctx.send(embed=embed)

    @commands.group(aliases=["to-do"], invoke_without_command=True)
    async def todo(self, ctx: utils.CustomContext):
        """Base command for all to-do commands."""

        await ctx.send_help(ctx.command)

    @todo.command(name="add")
    async def todo_add(self, ctx: utils.CustomContext, *, task: str):
        """Adds a task to your to-do list."""

        if len(task) > 100:
            raise commands.BadArgument(
                "Your task can not be longer than 100 characters.")

        sql = "INSERT INTO todos VALUES(DEFAULT, $1, $2)"
        values = (ctx.author.id, task)
        await self.bot.pool.execute(sql, *values)

        await ctx.send("Successfully added that to your to-do list.")

    @todo.command(name="bulkadd", aliases=["bulk_add", "badd"])
    async def todo_bulk_add(self, ctx: utils.CustomContext, *tasks: str):
        """Bulk adds tasks to your to-do list.
        A couple of tasks may look like:
        `{prefix}to-do bulkadd "Wow one task here" "Wow here's another task"`."""

        if len(tasks) > 10:
            raise commands.BadArgument(
                "You can not insert more than 10 tasks at a time.")

        values = []

        for task in tasks:
            if len(task) > 100:
                raise commands.BadArgument(
                    "I couldn't add one of your tasks as they were above 100 characters.")

            values.append((ctx.author.id, task))

        sql = "INSERT INTO todos VALUES(DEFAULT, $1, $2)"
        await self.bot.pool.executemany(sql, values)

        await ctx.send("Successfully added those tasks to your to-do list.")

    @todo.command(name="remove", aliases=["delete", "del"])
    async def todo_remove(self, ctx: utils.CustomContext, *todo_ids: typing.Union[int, str]):
        """Removes one or many of your to-do tasks by its ID.
        Do: `{prefix}to-do remove *` to remove all of your tasks."""

        if todo_ids[0] == "*":
            sql = "DELETE FROM todos WHERE user_id = $1"
            await self.bot.pool.execute(sql, ctx.author.id)
            return await ctx.send("Successfully removed all of your current tasks.")

        values = []

        for todo_id in todo_ids:
            _id = await self._get_task_by_enumeration(ctx.author, todo_id)
            values.append((ctx.author.id, _id))

        sql = "DELETE FROM todos WHERE user_id = $1 AND id = $2"
        await self.bot.pool.executemany(sql, values)
        await ctx.send(f"Successfully deleted {len(todo_ids)} of your tasks.")

    @todo.command(name="edit")
    async def todo_edit(self, ctx: utils.CustomContext, task_id: int, *, task: str):
        """Edits a given task id with a new task description."""

        _id = await self._get_task_by_enumeration(ctx.author, task_id)
        sql = "UPDATE todos SET task = $1 WHERE id = $2"
        values = (task, _id)
        await self.bot.pool.execute(sql, *values)

        await ctx.send("Alright, updated that task for you!")

    @todo.command(name="list")
    async def todo_list(self, ctx: utils.CustomContext, flag: str = None):
        """Gives a list of all of your currently set tasks.
        You can also sort them with these flags:
        `--alphabetical` - Sorts all tasks in alphabetical order.
        `--size` - Sorts all tasks by size.
        Note: If you try to delete a task that is in one of these orders you may delete another task by accident!"""

        sql = "SELECT * FROM todos WHERE user_id = $1"

        if flag:
            parser = argparse.ArgumentParser()
            parser.add_argument("--alphabetical", action="store_true")
            parser.add_argument("--size", action="store_true")

            try:
                args = parser.parse_args([flag])
            except SystemExit:
                raise commands.BadArgument(
                    "The only available flags are `--alphabetical` and `--size`.")

            if args.alphabetical:
                sql += " ORDER BY task ASC"
            if args.size:
                sql += " ORDER BY CHAR_LENGTH(task) ASC"

        results = await self.bot.pool.fetch(sql, ctx.author.id)

        if not results:
            raise utils.NoTodoItems("You have no to-do items I can show you.")

        todo_list = []

        for item in results:
            todo_list.append(item["task"])

        source = utils.GeneralPageSource(todo_list, per_page=10)
        paginator = utils.KalPages(source)

        await paginator.start(ctx)

    @commands.command(name="id", aliases=["idof"])
    async def _id(self, ctx: utils.CustomContext, *, thing: AllConverter):
        """Gets the ID of a given user, role, emoji (Custom only), text channel or voice channel."""

        embed = self.bot.embed(ctx)
        embed.description = (
            f"The type of that is: {thing[1]}\n"
            f"The ID of it is: {thing[0]}"
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def convert(self, ctx: utils.CustomContext, amount: float, cur_from: str, cur_to: str):
        """Converts a given amount of money from one currency (3 letter e.g. GBP) to another currency."""

        currency_converter = CurrencyConverter()
        cur_from = cur_from.upper()
        cur_to = cur_to.upper()

        try:
            conversion = currency_converter.convert(amount, cur_from, cur_to)
        except ValueError:
            return await ctx.send("That is an unsupported currency.")

        await ctx.send(f"{amount} {cur_from} -> {cur_to} = {conversion:,.2f}")

    @commands.command(aliases=["g"], cooldown_after_parsing=True)
    @commands.cooldown(5, 5, commands.BucketType.user)
    async def google(self, ctx: utils.CustomContext, *, query: str):
        """Searches google for a given query."""

        async with self.google_search(query) as results:
            if not results:
                return await ctx.send("That query returned no results.")

            embeds = []

            for result in results:
                embed = self.bot.embed(ctx)
                embed.title = result.title
                embed.description = result.snippet
                embed.url = result.link
                embed.set_image(url=result.image if result.image is not None
                                and result.image.startswith(("https://", "http://"))
                                else discord.Embed.Empty)

                embeds.append(embed)

            menu = menus.MenuPages(utils.EmbedMenu(
                embeds), clear_reactions_after=True)
            await menu.start(ctx)

    # noinspection PyUnresolvedReferences
    @commands.command(aliases=["color"])
    async def colour(self, ctx: utils.CustomContext, *, colour: ColourConverter):
        """Shows a representation of a given colour.
        To get a random colour just do: {prefix}colour random"""

        rgb = colour.to_rgb()
        url = f"https://kal-byte.co.uk/colour/{'/'.join([str(x) for x in rgb])}"

        embed = self.bot.embed(
            ctx,
            colour=discord.Colour.from_rgb(*rgb)
        )

        embed.set_thumbnail(url=url)
        embed.add_field(name="Hex", value=f"{colour}", inline=False)
        embed.add_field(name="RGB", value=f"{rgb}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["av"])
    async def avatar(self, ctx: utils.CustomContext, member: typing.Optional[discord.Member]):
        """Get your own or another persons avatar."""

        member = member or ctx.author

        embed = self.bot.embed(ctx)
        embed.set_author(name=member, icon_url=member.avatar_url)
        embed.set_image(url=member.avatar_url_as(
            static_format="png", size=1024))
        await ctx.send(embed=embed)

    @commands.command(aliases=["about"])
    async def info(self, ctx: utils.CustomContext):
        """Get basic info on the bot."""

        astro = await self.bot.fetch_user(285506580919877633)
        embed = self.bot.embed(ctx)
        embed.title = "Info about Travis Bott"
        embed.description = f"Thank you to {astro} for designing the bots profile pictures!"
        embed.url = "https://www.travisbott.rocks/"

        embed.set_thumbnail(url=str(self.bot.user.avatar_url_as(
            format="png",
            static_format="png",
            size=1024)))

        developer = [str(self.bot.get_user(x)) for x in self.bot.owner_ids][0]

        guild_count = len(self.bot.guilds)

        member_count = sum(
            g.member_count for g in self.bot.guilds if not g.unavailable)

        process = psutil.Process(os.getpid())
        memory_used = process.memory_info().rss / 1024 ** 2
        memory_info = psutil.virtual_memory()

        cpu_percentage = psutil.cpu_percent()
        fields = [
            ["Invite", f"[Invite the bot here!]({self.bot.invite_url})", True],
            ["Need Support?",
                f"[Join the support server here]({self.bot.support_url})", True],
            ["Want to support the bot?",
                "[Click here!](https://top.gg/bot/706530005169209386)", True],
            ["Current Ping", f"{(self.bot.latency * 1000):,.2f} ms", True],
            ["Developer", f"{developer}", True],
            ["Guild Count", f"{guild_count}", True],
            ["User Count", f"{member_count:,}", True],
            ["Memory usage",
                f"{int(memory_used):,}/{int(memory_info.total / 1024 ** 2):,} MB", True],
            ["CPU usage", f"{cpu_percentage}%", True],
        ]
        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def emoji(self, ctx: utils.CustomContext, *emojis: discord.PartialEmoji):
        """Get's the full image of an emoji and adds some more info.
        ~~If you have `manage_emojis` permissions if you react with the detective, the emoji gets added to the server.~~"""

        embed_list = []

        if len(emojis) == 0:
            return await ctx.send_help(ctx.command)

        for emoji in emojis:
            embed = self.bot.embed(
                ctx,
                title=f"Showing for {emoji.name}",
                description=f"ID: {emoji.id}"
            )

            embed.url = str(emoji.url)

            embed.set_image(url=emoji.url)
            embed.add_field(name="Animated", value=emoji.animated)

            embed_list.append(embed)

        embed_pages = utils.EmbedMenu(embed_list)

        menu = utils.KalPages(embed_pages)
        await menu.start(ctx)

    @emoji.command(name="steal")
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    @utils.has_voted()
    async def steal_emoji(self, ctx: utils.CustomContext, emoji: discord.PartialEmoji, *, name: str = None):
        """Steals a given emoji and you're able to give it a new name.
        Permissions needed: `Manage Emojis`"""

        emoji_name = name or emoji.name

        emoji_bytes = await emoji.url.read()

        try:
            new_emoji = await ctx.guild.create_custom_emoji(
                name=emoji_name, image=emoji_bytes, reason=f"Responsible user: {ctx.author}"
            )
        except discord.Forbidden:
            return await ctx.send(
                "I could not add that emoji due to the server being at its emoji limit."
            )

        await ctx.send(
            f"Successfully stolen {new_emoji} with the name `{new_emoji.name}`"
        )

    @emoji.command(name="fromid")
    @commands.has_permissions(manage_emojis=True)
    async def steal_emoji_from_id(
        self, ctx: utils.CustomContext, gif_or_png: str, emoji_id: int, *, name: str = None
    ):
        """Steals a given emoji by its ID you're able to give it a new name.
        Permissions needed: `Manage Emojis`"""

        if gif_or_png not in ["gif", "png"]:
            return await ctx.send_help(ctx.command)

        emoji_name = name or str(emoji_id)

        url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{gif_or_png}"

        async with self.bot.session.get(url) as r:
            if r.status != 200:
                return await ctx.send("You probably didn't use the right ID.")
            emoji_bytes = await r.read()

            new_emoji = await ctx.guild.create_custom_emoji(
                name=emoji_name,
                image=emoji_bytes,
                reason=f"Responsible user: {ctx.author}",
            )

            await ctx.send(
                f"Successfully stolen {new_emoji} with the name `{new_emoji.name}`"
            )

    @emoji.error
    async def on_emoji_error(self, ctx: utils.CustomContext, error):
        if isinstance(error, commands.PartialEmojiConversionFailure):
            return await ctx.send("I could not convert that emoji.")

    @commands.command(aliases=["server"])
    async def serverinfo(self, ctx: utils.CustomContext):
        """Gives you information based on the current server"""

        guild_features = []
        title = f"Information on {ctx.guild.name}"
        icon = ctx.guild.icon_url

        features_dict = {
            "VIP_REGIONS": "VIP Voice Servers",
            "PARTNERED": "Partnered",
            "VERIFIED": "Verified",
            "DISCOVERABLE": "Discoverable",
            "COMMUNITY": "Community Server",
            "ANIMATED_ICON": "Animated Icon",
            "BANNER": "Banner",
        }

        features = set(ctx.guild.features)

        for feature, label in features_dict.items():
            if feature in features:
                guild_features.append(f"✅: {label}")

        human_count = sum(not m.bot for m in ctx.guild.members)
        bot_count = sum(m.bot for m in ctx.guild.members)

        info = [
            ["Emoji Count", sum(e.available for e in ctx.guild.emojis), True],
            [
                "Member Count",
                f"{ctx.guild.member_count}\nHumans: {human_count} Bots: {bot_count}",
                True,
            ],
            ["Boosters", sum(1 for m in ctx.guild.premium_subscribers), True],
            ["Role Count", sum(1 for role in ctx.guild.roles), True],
            ["Voice Region", str(ctx.guild.region), True],
            ["AFK Channel", str(ctx.guild.afk_channel or "None"), True],
            [
                "<:text_channel:762721785502236716> / <:voice_channel:762721785984188436>",
                f"{sum(1 for tc in ctx.guild.text_channels)} / {sum(1 for vc in ctx.guild.voice_channels)}",
                True,
            ],
            ["Features", "\n".join(guild_features) or "None", False],
        ]

        embed = self.bot.embed(
            ctx,
            title=title,
            description=f"**ID:** {ctx.guild.id}\n**Owner:** {ctx.guild.owner}",
            thumbnail=icon if ctx.guild.icon else discord.Embed.Empty(),
            footer_text="Created at ",
            timestamp=ctx.guild.created_at,
        )

        [embed.add_field(name=k, value=v, inline=i) for k, v, i in info]

        await ctx.send(embed=embed)

    @commands.command()
    async def channel(self, ctx: utils.CustomContext, channel: typing.Union[discord.TextChannel, discord.VoiceChannel] = None):
        """Gives you information on a channel."""

        channel = channel or ctx.channel

        embed = self.bot.embed(
            ctx,
            title=f"Information on {channel.name}"
        )

        channel_topic = channel.topic or "No Topic" if isinstance(
            channel, discord.TextChannel) else "No Topic"

        fields = [
            ["Channel Type:", f"{channel.type}"],
            ["Channel Category:", f"{channel.category.name}"],
            ["Created At:",
                f"{utils.format_time(channel.created_at)['date']}"],
        ]

        if isinstance(channel, discord.TextChannel):
            fields.append(["Channel Topic:", f"{channel_topic}"])

        if isinstance(channel, discord.VoiceChannel):
            fields.append(
                [f"Currently Connected ({len(channel.members)})",
                 f"{' '.join([m.name for m in channel.members]) or None}"]
            )
            fields.append(
                [f"Bitrate", f"{channel.bitrate}"]
            )
            fields.append(
                [f"User Limit", f"{channel.user_limit}"]
            )

        [embed.add_field(name=n, value=v, inline=False) for n, v in fields]
        await ctx.send(embed=embed)

    @commands.command(aliases=["urban", "ud"])
    async def urbandictionary(self, ctx: utils.CustomContext, *, definition: str):
        """Get a urban dictionary definition of almost any word!"""

        if len(definition) == 0:
            return await ctx.send(
                "You need to give me something you want to get the definition of..."
            )

        if " " in definition:
            definition = definition.replace(" ", "-")
        url = "http://api.urbandictionary.com/v0/define?term=" + definition
        async with self.bot.session.get(url) as response:
            if response.status != 200:
                return await ctx.send("Couldn't find that or something really bad just happened.")

            data = await response.json()

            if not data["list"]:
                return await ctx.send("There were no results for that look up.")

            word = data["list"][0]["word"]
            author = data["list"][0]["author"]
            definition = data["list"][0]["definition"]
            example = data["list"][0]["example"]
            thumbs_up = data["list"][0]["thumbs_up"]
            thumbs_down = data["list"][0]["thumbs_down"]
            perma_link = data["list"][0]["permalink"]

            if len(definition) > 1024 or len(example) > 1024:
                return await ctx.send(
                    "The lookup for this word is way too big to show."
                )

            embed = self.bot.embed(
                ctx,
                title=f"Definition of {word}"
            )

            embed.set_footer(text=f"Definition by: {author}")
            embed.url = perma_link

            embed.set_author(
                name=f"Requested by: {ctx.author.name}",
                icon_url=ctx.author.avatar_url,
            )
            embed.add_field(name="Definition:",
                            value=definition, inline=False)
            embed.add_field(name="Example:", value=example, inline=False)
            embed.add_field(name="\N{THUMBS UP SIGN}",
                            value=thumbs_up, inline=True)
            embed.add_field(
                name="\N{THUMBS DOWN SIGN}", value=thumbs_down, inline=True
            )

            await ctx.send(embed=embed)

    @commands.command(aliases=["calc"])
    async def calculate(self, ctx: utils.CustomContext, *, equation: str = None):
        """Gives you the answer to (basic) calculations."""

        if "x" in equation:
            equation = equation.replace("x", "*")
        result = numexpr.evaluate(str(equation)).item()
        embed = self.bot.embed(
            ctx,
            title=f"Result of {equation}:",
            description=f"{result}"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["userinfo", "ui"])
    @commands.guild_only()
    async def whois(self, ctx: utils.CustomContext, user: discord.Member = None):
        """Gives you basic information on someone."""

        user = user or ctx.author
        colour = self._get_top_coloured_role(user)
        embed = self.bot.embed(ctx)
        embed.colour = colour
        embed.title = f"About {user.name}"
        embed.description = (
            f"**ID**: {user.id}\n"
            f"**Bot**: {user.bot}\n"
            f"{'**Is literally the bot owner**' if user.id in self.bot.owner_ids else ''}"
        )
        embed.set_thumbnail(url=user.avatar_url)

        created_at = (
            f"{utils.format_time(user.created_at)['date']} "
            f"({humanize.naturaltime(user.created_at)})"
        )

        joined_at = (
            f"{utils.format_time(user.joined_at)['date']} "
            f"({humanize.naturaltime(user.joined_at)})"
        )

        roles = user.roles[1:]
        roles.reverse()
        roles = [r.mention for r in roles][:30]

        def get_boost(u: discord.Member):
            """Quick function to check if a user is boosting."""

            if u.premium_since is None:
                return "No"
            else:
                return f"{utils.format_time(u.premium_since)['date']} ({humanize.naturaltime(u.premium_since)})"

        boost = get_boost(user)

        embed.add_field(name="Account created",
                        value=f"{created_at}")

        embed.add_field(name="User joined date",
                        value=f"{joined_at}")

        embed.add_field(name="Boosting",
                        value=f"{boost}")

        embed.add_field(name=f"Roles [{len(roles) if len(roles) < 30 else '30*'}]",
                        value=" ".join(roles) or "No roles.",
                        inline=False)

        embed.add_field(name="Permissions",
                        value=utils.check_permissions(ctx, user),
                        inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def weather(self, ctx: utils.CustomContext, *, city_or_country: str):
        """Gives the weather of a given country/city."""

        url = f"http://api.openweathermap.org/data/2.5/weather?appid={self.weather_api_key}&q={city_or_country}"
        async with self.bot.session.get(url) as r:
            if r.status != 200:
                return await ctx.send(
                    f"Could not find that city/country ||Status Code: {r.status}||"
                )
            data = await r.json()
            main = data["main"]
            weather = data["weather"][0]

            temp_celcius = round(int(main["temp"]) - 273.15)
            temp_fahrenheit = (temp_celcius * 9 / 5) + 32
            pressure = main["pressure"]
            humidity = main["humidity"]

            description = weather["description"]
            icon = f"https://openweathermap.org/img/wn/{weather['icon']}@4x.png"

            fields = [
                ["Temperature", f"{temp_celcius}°C | {temp_fahrenheit}°F"],
                ["Pressure", f"{pressure} hPa"],
                ["Humidity", f"{humidity}%"],
                ["Description", description],
            ]

            embed = self.bot.embed(
                ctx,
                title=f"Weather in {data['name']}"
            )
            embed.set_thumbnail(url=icon)
            [embed.add_field(name=n, value=v, inline=False) for n, v in fields]
            await ctx.send(embed=embed)

    @commands.command()
    async def country(self, ctx: utils.CustomContext, *, country: str):
        """Gives basic information on a given country."""

        complete_api_url = f"https://restcountries.eu/rest/v2/name/{country}"
        async with self.bot.session.get(complete_api_url) as r:
            if r.status != 200:
                return await ctx.send("I could not find that country.")
            data = await r.json()
            data = data[0]
            fields = [
                ["Name:", data["nativeName"]],
                ["2 Letter Code:", data["alpha2Code"]],
                ["Capital City: ", data["capital"]],
                ["Continent", data["region"]],
                ["Population:", f"{data['population']:,}"],
                [
                    "Currency:",
                    f"{data['currencies'][0]['name']} ({data['currencies'][0]['symbol']})",
                ],
                ["Language Spoken:", data["languages"][0]["nativeName"]],
            ]

            embed = self.bot.embed(ctx)
            [embed.add_field(name=n, value=str(v)) for n, v in fields]

            await ctx.send(embed=embed)

    @commands.command()
    async def poll(self, ctx: utils.CustomContext, *, query: str):
        """Poll System:
        To create a standard poll just do:
        {prefix}poll [Poll Question Here]
        To create a multiple choice poll do:
        {prefix}poll Question Here ? Choices, Here, Split, By, Commas
        """

        if len(multi := query.split(" ? ")) > 1:
            emojis = []

            for i in range(11):
                if i == 10:
                    emojis.append("\N{KEYCAP TEN}")

                emojis.append(
                    f"{i}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}")

            embed = self.bot.embed(ctx,
                                   title=multi[0],
                                   description="")

            choices = multi[1].split(", ")

            if len(choices) > 11:
                raise commands.BadArgument(
                    "You can not provide more than 10 options!")

            for index, choice in enumerate(choices):
                embed.description += f"{emojis[index]} {choice}\n"

            msg = await ctx.send(embed=embed)

            for index, choice in enumerate(choices):
                await msg.add_reaction(emojis[index])
        else:
            emojis = [
                "\N{THUMBS UP SIGN}",
                "\N{THUMBS DOWN SIGN}"
            ]
            embed = self.bot.embed(ctx, title=query)

            msg = await ctx.send(embed=embed)

            for emoji in emojis:
                await msg.add_reaction(emoji)


def setup(bot):
    bot.add_cog(Meta(bot, "🤖 Meta"))
