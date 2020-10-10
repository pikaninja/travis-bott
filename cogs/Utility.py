from decouple import config
from discord.ext import commands
from discord.ext import menus

from utils import utils
from aiohttp import request

from datetime import datetime as dt

import aiohttp
import psutil
import discord
import typing
import random
import numexpr
import asyncio
from io import StringIO

status_icons = {
    "online": "<:online:748253316693098609>",
    "dnd": "<:dnd:748253316777115659>",
    "idle": "<:away:748253316882104390>",
    "offline": "<:offline:748253316533846179>"
}

class Utility(commands.Cog, name="📝 Utility"):
    """Useful little utilities"""
    def __init__(self, bot):
        self.bot = bot
        self.weather_api_key = config("WEATHER_API_KEY")
        self.ksoft_api_key = config("KSOFT_API")

    @commands.command()
    async def translate(self, ctx, *, text: str):
        """Automatically translates a given text to English"""

        translation = await self.bot.translate_api.translate(str(text), dest="en")
        embed = utils.embed_message(title="Translation",
                                    message=str(translation.text),
                                    footer_text=f"Translated to English from {translation.src} - Confidence: {translation.confidence}")
        
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def emoji(self, ctx, emoji: discord.PartialEmoji):
        """Get's the full image of an emoji and adds some more info.
        If you have `manage_emojis` permissions if you react with the detective, the emoji gets added to the server."""

        embed = utils.embed_message(title=f"Showing for {emoji.name}",
                                    message=f"ID: {emoji.id}",
                                    url=str(emoji.url))

        embed.set_image(url=emoji.url)
        embed.add_field(name="Animated", value=emoji.animated)

        msg = await ctx.send(embed=embed)

        user_permissions: discord.Permissions = ctx.author.permissions_in(ctx.channel)
        if user_permissions.manage_emojis:
            await msg.add_reaction("🕵️‍♀️")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == "🕵️‍♀️" and reaction.message == msg
            
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await msg.remove_reaction("🕵️‍♀️", ctx.guild.me)
            else:
                emoji_bytes = await emoji.url.read()
                await ctx.guild.create_custom_emoji(name=emoji.name, image=emoji_bytes, reason=f"Responsible user: {ctx.author}")
                embed.set_footer(text="Successfully stolen that emoji!")
                await msg.edit(embed=embed)

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
    async def steal_emoji_from_id(self, ctx, emoji_id: int, *, name: str = None):
        """Steals a given emoji by its ID you're able to give it a new name.
        Permissions needed: `Manage Emojis`"""

        emoji_name = name or str(emoji_id)

        url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"

        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as r:
                emoji_bytes = await r.read()

                new_emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=emoji_bytes, reason=f"Responsible user: {ctx.author}")

                await ctx.send(f"Successfully stolen {new_emoji} with the name `{new_emoji.name}`")

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

        info = [
            ["Emoji Count", str(len(ctx.guild.emojis)), True],
            ["Member Count", f"{ctx.guild.member_count}\nHumans: {len([m for m in ctx.guild.members if not m.bot])} Bots: {len([m for m in ctx.guild.members if m.bot])}", True],
            ["Boosters", str(len(ctx.guild.premium_subscribers)), True],
            ["Role Count", str(len(ctx.guild.roles)), True],
            ["Voice Region", str(ctx.guild.region), True],
            ["AFK Channel", str(ctx.guild.afk_channel), True],
            ["<:text_channel:762721785502236716> / <:voice_channel:762721785984188436>", f"{len(ctx.guild.text_channels)} / {len(ctx.guild.voice_channels)}", True],
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
            ["How many can see this:", f"{len(channel.members)}"],
            #["Last Message:", f"{channel.last_message.content or 'Not Available'}"],
            ["Channel Category:", f"{channel.category.name}"],
            ["Created At:", f"{channel.created_at}"]
        ]

        [embed.add_field(name=n, value=v) for n, v in fields]
        await ctx.send(embed=embed)

    @commands.command(enabled=False)
    async def tester(self, ctx):
        """test"""

        default_pfps = [
            "https://cdn.discordapp.com/embed/avatars/0.png",
            # "https://cdn.discordapp.com/embed/avatars/1.png",
            # "https://cdn.discordapp.com/embed/avatars/2.png",
            # "https://cdn.discordapp.com/embed/avatars/3.png",
            # "https://cdn.discordapp.com/embed/avatars/4.png"
        ]

        default_av_bytes = []

        for av in default_pfps:
            async with request("GET", url=av, headers={}) as r:
                content = await r.content.read()
                pfp_bytes = StringIO(str(content)).read()
                default_av_bytes.append(pfp_bytes)

        avatar_bytes = await ctx.author.avatar_url.read()
        print(avatar_bytes in default_av_bytes)

        print(avatar_bytes)

        if avatar_bytes in default_av_bytes:
            await ctx.send("Hey")
        else:
            await ctx.send("Sup")

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
            if isinstance(user.activity, discord.Spotify):
                track = f"https://open.spotify.com/track/{user.activity.track_id if not None else 'None'}"
                activities = [
                    f"{', '.join(user.activity.artists)} - {user.activity.title}",
                    f"Duration: {str(user.activity.duration).split('.')[0]}",
                    f"URL: {track}"
                ]
            elif isinstance(user.activity, discord.BaseActivity):
                activities = [f"{user.activity.name}"]
            else:
                activities = ["Currently doing nothing, they might just have their game or spotify hidden."]
            return activities

        # async def check_if_bot(m: discord.Member):
        #     if dt.now().month == m.created_at.month or \
        #         dt.now().month - 1 == m.created_at.month:
        #         return "Potentially a bot 😳"
        #     return "Should be clear."

        async def check_if_bot(m: discord.Member):
            is_banned = await self.bot.kclient.bans.check(m.id)
            if dt.now().month == m.created_at.month and dt.now().year == m.created_at.year or \
                dt.now().month - 1 == m.created_at.month and dt.now().year == m.created_at.year:
                if is_banned:
                    prefix = "Pretty certain a "
                else:
                    prefix = "Potentially a "
                return prefix + "bot"
            if is_banned:
                prefix = " You may want to keep an eye out though."
            else:
                prefix = " Pretty sure they're safe"
            return "Should be clear." + prefix

        roles = user.roles[1:]
        roles.reverse()
        [user_roles.append(role.mention) for role in roles if len(user_roles) < 30]
        readable_roles = " ".join(user_roles)

        fields = [
            ["Username", f"{user}", True],
            ["Bot / User Bot", f"{user.bot} / {await check_if_bot(user)}", True],
            ["Status", f"{status_icons[str(user.status)]}  {str(user.status).capitalize()}", True],
            ["Created at", created_at_str, True],
            ["Joined at", joined_at_str, True],
            ["Boosting", check_boosted(user), True],
            [f"Roles [{len(user_roles) if len(user_roles) < 30 else '30*'}]", readable_roles, False],
            ["Permissions", utils.check_permissions(ctx, user), False],
            [f"Activity - {user.activity.type.name.capitalize() if user.activity else 'No Activity'}:", "\n".join(get_activity(user)), False]
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
    bot.add_cog(Utility(bot))