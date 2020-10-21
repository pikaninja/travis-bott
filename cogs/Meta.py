import logging
import async_cse

from decouple import config
from discord.ext import commands
from discord.ext import menus
import ksoftapi

from utils import utils
from utils.Paginator import Paginator
from aiohttp import request

from datetime import datetime as dt
from io import StringIO

from currency_converter import CurrencyConverter
import aiogoogletrans as translator

import aiohttp
import psutil
import discord
import typing
import random
import numexpr
import asyncio
import re

status_icons = {
    "online": "<:online:748253316693098609>",
    "dnd": "<:dnd:748253316777115659>",
    "idle": "<:away:748253316882104390>",
    "offline": "<:offline:748253316533846179>"
}

class Meta(commands.Cog, name="🤖 Meta"):
    """General and utility commands"""
    def __init__(self, bot):
        self.bot = bot
        self.weather_api_key = config("WEATHER_API_KEY")

    @commands.command()
    async def convert(self, ctx, amount: int, cur_from: str, cur_to: str):
        """Converts a given amount of money from one currency (3 letter e.g. GBP) to another currency."""
        
        currency_converter = CurrencyConverter()
        cur_from = cur_from.upper()
        cur_to = cur_to.upper()

        try:
            conversion = currency_converter.convert(amount, cur_from, cur_to)
        except ValueError:
            return await ctx.send("That is an unsupported currency.")

        await ctx.send(f"{amount} {cur_from} -> {cur_to} = {conversion:,.2f}")

    @commands.command()
    async def google(self, ctx, *, query: str):
        """Searches google for a given query."""

        cse = async_cse.Search(config("GOOGLE_CSE"))
        results = await cse.search(query, safesearch=True)

        how_many = 10 if len(results) > 10 else len(results)

        embed_list = []

        for i in range(how_many):
            embed = utils.embed_message()
            embed.title = results[i].title
            embed.description = results[i].description
            embed.url = results[i].url
            embed.set_image(url=results[i].image_url)

            embed_list.append(embed)

        p = Paginator(embed_list, delete_after=True)
        await p.paginate(ctx)
        await cse.close()

    @commands.command(aliases=["randomcolor", "rcolour", "rcolor"])
    async def randomcolour(self, ctx):
        """Gives a random colour."""

        r_colour = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        rgb_to_hex = "#%02x%02x%02x" % r_colour
        colour_representation = f"https://some-random-api.ml/canvas/colorviewer?hex={rgb_to_hex[1:]}"
        embed = utils.embed_message(title="Generated Colour",
                                    colour=discord.Colour.from_rgb(r_colour[0], r_colour[1], r_colour[2]))
        embed.set_thumbnail(url=colour_representation)
        embed.add_field(name="Hex", value=f"{rgb_to_hex}", inline=False)
        embed.add_field(name="RGB", value=f"{r_colour}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["color"])
    async def colour(self, ctx, colour: str):
        """Shows a representation of a given colour"""

        hex_regex = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"

        if not re.match(hex_regex, colour):
            return await ctx.send("The colour must be a properly formed **hex** colour.")

        colour_representation = f"https://some-random-api.ml/canvas/colorviewer?hex={colour[1:]}"
        hex_to_rgb = utils.hex_to_rgb(colour[1:])
        embed = utils.embed_message(colour=discord.Colour.from_rgb(hex_to_rgb[0], hex_to_rgb[1], hex_to_rgb[2]))
        embed.set_thumbnail(url=colour_representation)
        embed.add_field(name="Hex", value=f"{colour}", inline=False)
        embed.add_field(name="RGB", value=f"{hex_to_rgb}", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["av"])
    async def avatar(self, ctx, member: typing.Optional[discord.Member]):
        """Get your own or another persons avatar."""

        if not member:
            member = ctx.author
        
        embed = utils.embed_message()
        embed.set_author(name=member, icon_url=member.avatar_url)
        embed.set_image(url=member.avatar_url_as(static_format="png", size=1024))
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["latency"])
    async def ping(self, ctx):
        """Get the bots ping."""

        embed = utils.embed_message(message=f"**{int(ctx.bot.latency * 1000)} ms**")
        embed.set_author(name="Travis Bott's Latency:", icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)
    
    @commands.command()
    async def info(self, ctx):
        """Get basic info on the bot."""

        invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot"

        astro_user = await self.bot.fetch_user(285506580919877633)

        cpu_percentage = psutil.cpu_percent()
        mem_used = (psutil.virtual_memory().total - psutil.virtual_memory().available) / 1000000
        total_mem = psutil.virtual_memory().total / 1000000

        embed = utils.embed_message(title=f"Info about {self.bot.user.name}",
                                    message=f"Thank you to {astro_user} for making the avatar.",
                                    footer_text=f"Bot Version: {self.bot.version} | D.py Version: {discord.__version__}")
        embed.add_field(name="Invite the bot", value=f"[Here]({invite_link})")
        embed.add_field(name="GitHub", value=f"[Here]({config('GITHUB_LINK')})")
        embed.add_field(name="Support server", value=f"[Here]({config('SUPPORT_LINK')})")
        embed.add_field(name="Ping", value=f"{round(self.bot.latency * 1000)} ms")
        embed.add_field(name="Memory", value=f"{round(mem_used)} MB / {round(total_mem)} MB")
        embed.add_field(name="CPU", value=f"{cpu_percentage}%")
        embed.add_field(name="Creator", value=f"{config('DEVELOPER')}")
        embed.add_field(name="Currently in", value=f"{sum(1 for g in self.bot.guilds)} servers")
        embed.add_field(name="Current prefix", value=f"`{ctx.prefix}`")

        await ctx.send(embed=embed)

    @commands.command()
    async def translate(self, ctx, *, text: str):
        """Automatically translates a given text to English"""

        translate_api = translator.Translator()
        translation = await translate_api.translate(str(text), dest="en")
        embed = utils.embed_message(title="Translation",
                                    message=str(translation.text),
                                    footer_text=f"Translated to English from {translation.src} - Confidence: {translation.confidence}")
        
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def emoji(self, ctx, *emojis: discord.PartialEmoji):
        """Get's the full image of an emoji and adds some more info.
        ~~If you have `manage_emojis` permissions if you react with the detective, the emoji gets added to the server.~~"""

        embed_list = []

        for _ in range(len(emojis)):
            emoji = emojis[_]
            embed = utils.embed_message(title=f"Showing for {emoji.name}",
                                        message=f"ID: {emoji.id}",
                                        footer_text=f"Page {_ + 1}/{len(emojis)}",
                                        url=str(emoji.url))

            embed.set_image(url=emoji.url)
            embed.add_field(name="Animated", value=emoji.animated)

            embed_list.append(embed)

        emoji_menu = Paginator(
            embed_list,
            emojis=["\N{SLEUTH OR SPY}"],
            delete_after=False,
            timeout=120.0,
            clear_reactions=True
        )
        
        message = await emoji_menu.paginate(ctx)

        user_permissions: discord.Permissions = ctx.author.permissions_in(ctx.channel)
        if user_permissions.manage_emojis:
            await message.add_reaction("🕵️‍♀️")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == "🕵️‍♀️" and reaction.message == message
            
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await message.remove_reaction("🕵️‍♀️", ctx.guild.me)
            else:
                for emoji in emojis:
                    emoji_bytes = await emoji.url.read()
                    await ctx.guild.create_custom_emoji(name=emoji.name, image=emoji_bytes, reason=f"Responsible user: {ctx.author}")
                    await ctx.send("Successfully stole all emojis.")

    @emoji.command(name="steal")
    @commands.has_permissions(manage_emojis=True)
    async def steal_emoji(self, ctx, emoji: discord.PartialEmoji, *, name: str = None):
        """Steals a given emoji and you're able to give it a new name.
        Permissions needed: `Manage Emojis`"""

        emoji_name = name or emoji.name

        emoji_bytes = await emoji.url.read()
        new_emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=emoji_bytes, reason=f"Responsible user: {ctx.author}")

        await ctx.send(f"Successfully stolen {new_emoji} with the name `{new_emoji.name}`")
    
    @emoji.command(name="fromid")
    @commands.has_permissions(manage_emojis=True)
    async def steal_emoji_from_id(self, ctx, gif_or_png: str, emoji_id: int, *, name: str = None):
        """Steals a given emoji by its ID you're able to give it a new name.
        Permissions needed: `Manage Emojis`"""

        if gif_or_png not in ["gif", "png"]:
            return await ctx.send_help(ctx.command)

        emoji_name = name or str(emoji_id)

        url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{gif_or_png}"

        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as r:
                if r.status != 200:
                    return await ctx.send("You probably didn't use the right ID.")
                emoji_bytes = await r.read()

                new_emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=emoji_bytes, reason=f"Responsible user: {ctx.author}")

                await ctx.send(f"Successfully stolen {new_emoji} with the name `{new_emoji.name}`")

                await r.close()
                await cs.close()

    @emoji.error
    async def on_emoji_error(self, ctx, error):
        if isinstance(error, commands.PartialEmojiConversionFailure):
            return await ctx.send("I could not convert that emoji.")

    @commands.command(aliases=["server"])
    async def serverinfo(self, ctx):
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
            "BANNER": "Banner"
        }

        features = set(ctx.guild.features)

        for feature, label in features_dict.items():
            if feature in features:
                guild_features.append(f"✅: {label}")

        human_count = sum(not m.bot for m in ctx.guild.members)
        bot_count = sum(m.bot for m in ctx.guild.members)

        info = [
            ["Emoji Count", sum(e.available for e in ctx.guild.emojis), True],
            ["Member Count", f"{ctx.guild.member_count}\nHumans: {human_count} Bots: {bot_count}", True],
            ["Boosters", sum(1 for m in ctx.guild.premium_subscribers), True],
            ["Role Count", sum(1 for role in ctx.guild.roles), True],
            ["Voice Region", str(ctx.guild.region), True],
            ["AFK Channel", str(ctx.guild.afk_channel), True],
            ["<:text_channel:762721785502236716> / <:voice_channel:762721785984188436>", f"{sum(1 for tc in ctx.guild.text_channels)} / {sum(1 for vc in ctx.guild.voice_channels)}", True],
            ["Features", "\n".join(guild_features), False]
        ]

        embed = utils.embed_message(title=title,
                                    message=f"**ID:** {ctx.guild.id}\n**Owner:** {ctx.guild.owner}",
                                    thumbnail=icon if ctx.guild.icon else discord.Embed.Empty(),
                                    footer_text="Created at ",
                                    timestamp=ctx.guild.created_at)

        [embed.add_field(name=k, value=v, inline=i) for k, v, i in info]

        await ctx.send(embed=embed)

    @commands.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Gives you information on a channel."""

        channel: discord.TextChannel = channel or ctx.channel

        embed = utils.embed_message(title=f"Information on {channel.name}")
        fields = [
            ["Channel Topic:", f"{channel.topic or 'No Topic'}"],
            ["Channel Type:", f"{channel.type}"],
            ["How many can see this:", f"{sum(1 for member in channel.members)}"],
            #["Last Message:", f"{channel.last_message.content or 'Not Available'}"],
            ["Channel Category:", f"{channel.category.name}"],
            ["Created At:", f"{channel.created_at}"]
        ]

        [embed.add_field(name=n, value=v) for n, v in fields]
        await ctx.send(embed=embed)

    @commands.command(aliases=["urban", "ud"])
    async def urbandictionary(self, ctx, *, definition: str):
        """Get a urban dictionary definition of almost any word!"""

        if len(definition) == 0:
            return await ctx.send("You need to give me something you want to get the definition of...")

        if " " in definition:
            definition = definition.replace(" ", "-")
        url = "http://api.urbandictionary.com/v0/define?term=" + definition
        async with request("GET", url, headers={}) as response:
            if response.status == 200:
                data = await response.json()

                word = data["list"][0]["word"]
                author = data["list"][0]["author"]
                definition = data["list"][0]["definition"]
                example = data["list"][0]["example"]
                thumbs_up = data["list"][0]["thumbs_up"]
                thumbs_down = data["list"][0]["thumbs_down"]
                perma_link = data["list"][0]["permalink"]

                if len(definition) > 2000 or len(example) > 2000:
                    return await ctx.send("The lookup for this word is way too big to show.")

                embed = utils.embed_message(title=f"Definition of {word}",
                                            footer_text=f"Definition by: {author}",
                                            url=perma_link)
                embed.set_author(name=f"Requested by: {ctx.author.name}", icon_url=ctx.author.avatar_url)
                embed.add_field(name="Definition:", value=definition, inline=False)
                embed.add_field(name="Example:", value=example, inline=False)
                embed.add_field(name="\N{THUMBS UP SIGN}", value=thumbs_up, inline=True)
                embed.add_field(name="\N{THUMBS DOWN SIGN}", value=thumbs_down, inline=True)

                await ctx.send(embed=embed)
            else:
                return await ctx.send("Could not find that definition.")

    @commands.command(aliases=["calc"])
    async def calculate(self, ctx, *, equation: str = None):
        """Gives you the answer to (basic) calculations."""

        if "x" in equation:
            equation = equation.replace("x", "*")
        result = numexpr.evaluate(str(equation)).item()
        embed = utils.embed_message(title=f"Result of {equation}:",
                                    message=result)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def whois(self, ctx, user: discord.Member = None):
        """Gives you basic information on someone."""

        user = user or ctx.author
        user_id = user.id
        user_roles = []
        created_at_str = f"{user.created_at.day}/{user.created_at.month}/{user.created_at.year} {user.created_at.hour}:{user.created_at.minute}:{user.created_at.second}"
        joined_at_str = f"{user.joined_at.day}/{user.joined_at.month}/{user.joined_at.year} {user.joined_at.hour}:{user.joined_at.minute}:{user.joined_at.second}"
        
        def check_boosted(user: discord.Member):
            if user.premium_since is None:
                return "No"
            boosted_at_str = f"{user.premium_since.day}/{user.premium_since.month}/{user.premium_since.year} {user.premium_since.hour}:{user.premium_since.minute}:{user.premium_since.second}"
            return boosted_at_str

        def get_activity(m: discord.Member):
            activities = []
            if isinstance(m.activity, discord.Spotify):
                track = f"https://open.spotify.com/track/{m.activity.track_id if not None else 'None'}"
                activities = [
                    f"{', '.join(m.activity.artists)} - {m.activity.title}",
                    f"Duration: {str(m.activity.duration).split('.')[0]}",
                    f"URL: {track}"
                ]
            elif isinstance(m.activity, discord.CustomActivity):
                activities = [f"{m.activity.name}"]
            elif isinstance(m.activity, discord.Game):
                activities = [f"{m.activity.name}"]
            elif isinstance(m.activity, discord.Streaming):
                activities = [f"{m.activity.name}"]
            else:
                activities = ["Currently doing nothing, they might just have their game or spotify hidden."]
            return activities

        # async def check_if_bot(m: discord.Member):
        #     if dt.now().month == m.created_at.month or \
        #         dt.now().month - 1 == m.created_at.month:
        #         return "Potentially a bot 😳"
        #     return "Should be clear."

        async def check_if_bot(m: discord.Member):
            kclient = ksoftapi.Client(config("KSOFT_API"))
            if m.bot:
                return "This is literally a bot user."
            is_banned = await kclient.bans.check(m.id)
            if dt.now().month == m.created_at.month and dt.now().year == m.created_at.year or \
                dt.now().month - 1 == m.created_at.month and dt.now().year == m.created_at.year:
                if is_banned:
                    prefix = "Pretty certain a "
                else:
                    prefix = "Potentially a "
                await kclient.close()
                return prefix + "bot"
            if is_banned:
                prefix = " You may want to keep an eye out though."
            else:
                prefix = " Pretty sure they're safe"
            await kclient.close()
            return "Should be clear." + prefix
            

        roles = user.roles[1:]
        roles.reverse()
        [user_roles.append(role.mention) for role in roles if len(user_roles) < 30]
        readable_roles = " ".join(user_roles)

        fields = [
            ["Username", f"{user}", True],
            ["Bot / User Bot", f"{user.bot} / {await check_if_bot(user)}", True],
            ["Created at", created_at_str, True],
            ["Joined at", joined_at_str, True],
            ["Boosting", check_boosted(user), True],
            [f"Roles [{len(user_roles) if len(user_roles) < 30 else '30*'}]", readable_roles, False],
            ["Permissions", utils.check_permissions(ctx, user), False]
        ]

        embed = utils.embed_message(thumbnail=user.avatar_url,
                                    footer_text=f"ID: {user.id} | Powered by KSoft.Si API")
        [embed.add_field(name=n, value=v, inline=i) for n, v, i in fields]
        await ctx.send(embed=embed)

    @commands.command()
    async def weather(self, ctx, *, city_or_country: str):
        """Gives the weather of a given country/city."""

        url = f"http://api.openweathermap.org/data/2.5/weather?appid={self.weather_api_key}&q={city_or_country}"
        async with request("GET", url, headers={}) as r:
            if r.status != 200:
                return await ctx.send(f"Could not find that city/country ||Status Code: {r.status}||")
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
                ["Temperature", f"{temp_celcius}℃ | {temp_fahrenheit}℉"],
                ["Pressure", f"{pressure} hPa"],
                ["Humidity", f"{humidity}%"],
                ["Description", description]
            ]

            embed = utils.embed_message(title=f"Weather in {data['name']}",
                                        thumbnail=icon)
            [embed.add_field(name=n, value=v, inline=False) for n, v in fields]
            await ctx.send(embed=embed)

    # @commands.command()
    # async def steam(self, ctx, profile: str):
    #     """Gets a users steam profile and puts it in an embed."""

    #     complete_api_url = f"https://api.alexflipnote.dev/steam/user/{profile}"
    #     async with request("GET", complete_api_url, headers={}) as r:
    #         if r.status != 200:
    #             return await ctx.send("I could not find that profile.")
    #         data = await r.json()
    #         url = data["profile"]["url"]
    #         background = data["profile"]["background"]
    #         avatar = data["avatars"]["avatarfull"]
    #         steam_id = data["id"]["steamid32"]

    #         fields = [
    #             ["Username", data["profile"]["username"], True],
    #             ["Real Name", data["profile"]["realname"], True],
    #             ["Location", data["profile"]["location"], True],
    #             ["State", data["profile"]["state"], True],
    #             ["Date Created", data["profile"]["timecreated"], True],
    #             ["Vac Banned", data["profile"]["vacbanned"], True],
    #             ["Summary", "```\n" + data["profile"]["summary"] + "```", False],
    #         ]
            
    #         embed = utils.embed_message(title=f"Profile of {profile}",
    #                                     footer_text=f"Steam ID: {steam_id}",
    #                                     thumbnail=avatar,
    #                                     url=url)
    #         embed.set_image(url=background)

    #         [embed.add_field(name=n, value=str(v), inline=il) for n, v, il in fields]
            
    #         await ctx.send(embed=embed)

    @commands.command()
    async def country(self, ctx, *, country: str):
        """Gives basic information on a given country."""

        complete_api_url = f"https://restcountries.eu/rest/v2/name/{country}"
        async with request("GET", complete_api_url, headers={}) as r:
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
                ["Currency:", f"{data['currencies'][0]['name']} ({data['currencies'][0]['symbol']})"],
                ["Language Spoken:", data["languages"][0]["nativeName"]]
            ]
            
            embed = utils.embed_message()
            [embed.add_field(name=n, value=str(v)) for n, v in fields]
            
            await ctx.send(embed=embed)
    
    @commands.command()
    async def poll(self, ctx, mode: typing.Optional[int] = 0, *, query: str):
        """Starts a poll with a given query.
        Modes:
        0 (Default) -> Standard poll, adds Yes, No and Maybe emoji.
        1 -> Numbered poll, adds as many options as you give queries.
        Up to ten.
        
        Query:
        To have multiple options (for 1) seperate them with |"""

        if mode == 0:
            embed = utils.embed_message(message=str("".join(query)),
                                        footer_text="")
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            msg = await ctx.send(embed=embed)

            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
            await msg.add_reaction("🤷‍♀️")
        elif mode == 1:
            query = query.split("|")
            emojis = ["1️⃣", "2️⃣" ,"3️⃣" ,"4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            amount = len(query)

            if amount > 10:
                return await ctx.send("There are too many queries! We'll hopefully allow more soon.")

            embed = utils.embed_message(footer_text="")
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            print(query)
            for _ in range(amount):
                embed.add_field(name=str(_ + 1), value=query[_])
            
            msg = await ctx.send(embed=embed)

            for _ in range(amount):
                await msg.add_reaction(emojis[_])


def setup(bot):
    bot.add_cog(Meta(bot))