import cse
import contextlib
from contextlib import asynccontextmanager

import KalDiscordUtils
from decouple import config
from discord.ext import commands, menus
from discord.ext.commands.errors import BadArgument

import utils

from currency_converter import CurrencyConverter
import aiogoogletrans as translator

import psutil
import discord
import typing
import random
import numexpr
import re
import humanize

status_icons = {
    "online": "<:online:748253316693098609>",
    "dnd": "<:dnd:748253316777115659>",
    "idle": "<:away:748253316882104390>",
    "offline": "<:offline:748253316533846179>",
}

# Testing python-cse


@asynccontextmanager
async def google_search(query: str):
    """Context Manager to search for the CSE"""

    with contextlib.suppress(KeyError):
        keys = [config("GOOGLE_CSE"), config("SECOND_GOOGLE_CSE")]
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


class Meta(utils.BaseCog, name="meta"):
    """General and utility commands"""

    def __init__(self, bot, show_name):
        self.bot: utils.MyBot = bot
        self.show_name = show_name
        self.weather_api_key = config("WEATHER_API_KEY")

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

    @commands.command(aliases=["g"])
    @commands.cooldown(5, 5, commands.BucketType.user)
    async def google(self, ctx: utils.CustomContext, *, query: str):
        """Searches google for a given query."""

        async with google_search(query) as results:
            if not results:
                return await ctx.send("That query returned no results.")

            embeds = []

            for result in results:
                embed = KalDiscordUtils.Embed.default(ctx)
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

    @commands.command(aliases=["randomcolor", "rcolour", "rcolor"])
    async def randomcolour(self, ctx: utils.CustomContext):
        """Gives a random colour."""

        colour = discord.Colour.random()
        rgb = colour.to_rgb()

        colour_representation = (
            f"https://some-random-api.ml/canvas/colorviewer?hex={str(colour)[1:]}"
        )
        embed = KalDiscordUtils.Embed.default(
            ctx,
            title="Generated Colour",
            colour=colour,
        )
        embed.set_thumbnail(url=colour_representation)
        embed.add_field(name="Hex", value=f"{colour}", inline=False)
        embed.add_field(name="RGB", value=f"{rgb}", inline=False)
        await ctx.send(embed=embed)

    # noinspection PyUnresolvedReferences
    @commands.command(aliases=["color"])
    async def colour(self, ctx: utils.CustomContext, colour: commands.ColourConverter):
        """Shows a representation of a given colour"""

        colour_representation = (
            f"https://some-random-api.ml/canvas/colorviewer?hex={str(colour)[1:]}"
        )

        rgb = colour.to_rgb()

        embed = KalDiscordUtils.Embed.default(
            ctx,
            colour=discord.Colour.from_rgb(*rgb)
        )

        embed.set_thumbnail(url=colour_representation)
        embed.add_field(name="Hex", value=f"{colour}", inline=False)
        embed.add_field(name="RGB", value=f"{rgb}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["av"])
    async def avatar(self, ctx: utils.CustomContext, member: typing.Optional[discord.Member]):
        """Get your own or another persons avatar."""

        member = member or ctx.author

        embed = KalDiscordUtils.Embed.default(ctx)
        embed.set_author(name=member, icon_url=member.avatar_url)
        embed.set_image(url=member.avatar_url_as(
            static_format="png", size=1024))
        await ctx.send(embed=embed)

    @commands.command(aliases=["about"])
    async def info(self, ctx: utils.CustomContext):
        """Get basic info on the bot."""

        invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot"

        astro_user = await self.bot.fetch_user(285506580919877633)

        cpu_percentage = psutil.cpu_percent()
        mem_used = (
            psutil.virtual_memory().total - psutil.virtual_memory().available
        ) / 1000000
        total_mem = psutil.virtual_memory().total / 1000000

        embed = KalDiscordUtils.Embed.default(
            ctx,
            title=f"Info about {self.bot.user.name}",
            description=f"Thank you to {astro_user} for making the avatar."
        )

        embed.set_footer(
            text=f"Bot Version: {self.bot.version} | D.py Version: {discord.__version__}")

        embed.add_field(name="Invite the bot", value=f"[Here]({invite_link})")
        embed.add_field(
            name="GitHub", value=f"[Here]({config('GITHUB_LINK')})")
        embed.add_field(
            name="Support server", value=f"[Here]({config('SUPPORT_LINK')})"
        )
        embed.add_field(
            name="Ping", value=f"{round(self.bot.latency * 1000)} ms")
        embed.add_field(
            name="Memory", value=f"{round(mem_used)} MB / {round(total_mem)} MB"
        )
        embed.add_field(name="CPU", value=f"{cpu_percentage}%")
        embed.add_field(name="Creator", value=f"{config('DEVELOPER')}")
        embed.add_field(
            name="Currently in", value=f"{sum(1 for g in self.bot.guilds)} servers"
        )
        embed.add_field(name="Current prefix", value=f"`{(await self.bot.get_prefix(ctx.message))[2]}`")

        embed.set_image(url="https://kallum.pls-finger.me/rTZv0o.png")

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def emoji(self, ctx: utils.CustomContext, *emojis: discord.PartialEmoji):
        """Get's the full image of an emoji and adds some more info.
        ~~If you have `manage_emojis` permissions if you react with the detective, the emoji gets added to the server.~~"""

        embed_list = []

        if len(emojis) == 0:
            return await ctx.send_help(ctx.command)

        for _ in range(len(emojis)):
            emoji = emojis[_]
            embed = KalDiscordUtils.Embed.default(
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

        embed = KalDiscordUtils.Embed.default(
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

        embed = KalDiscordUtils.Embed.default(
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

            embed = KalDiscordUtils.Embed.default(
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
        embed = KalDiscordUtils.Embed.default(
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
        embed = KalDiscordUtils.Embed.default(ctx)
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

        async def get_boost(u: discord.Member):
            """Quick function to check if a user is boosting."""

            if u.premium_since is None:
                return "No"
            else:
                return f"{utils.format_time(u.premium_since)['date']} ({humanize.naturaltime(u.premium_since)})"

        boost = await get_boost(user)

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

            embed = KalDiscordUtils.Embed.default(
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

            embed = KalDiscordUtils.Embed.default(ctx)
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
            emojis = [
                "1️⃣",
                "2️⃣",
                "3️⃣",
                "4️⃣",
                "5️⃣",
                "6️⃣",
                "7️⃣",
                "8️⃣",
                "9️⃣",
                "🔟",
            ]
            embed = KalDiscordUtils.Embed.default(ctx,
                                                  title=multi[0],
                                                  description="")
            choices = multi[1].split(", ")
            for i in range(len(choices)):
                embed.description += f"{emojis[i]} {choices[i]}\n"

            msg = await ctx.send(embed=embed)

            for i in range(len(choices)):
                await msg.add_reaction(emojis[i])
        else:
            emojis = [
                "\N{THUMBS UP SIGN}",
                "\N{THUMBS DOWN SIGN}"
            ]
            embed = KalDiscordUtils.Embed.default(ctx,
                                                  title=query)

            msg = await ctx.send(embed=embed)

            for emoji in emojis:
                await msg.add_reaction(emoji)


def setup(bot):
    bot.add_cog(Meta(bot, "🤖 Meta"))
