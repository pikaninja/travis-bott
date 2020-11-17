import typing
from decouple import config
import discord
from discord.ext import commands

from utils import utils
from utils.CustomCog import BaseCog


class Misc(BaseCog, name="misc"):
    """Miscellaneous Commands"""

    def __init__(self, bot, show_name):
        self.bot = bot
        self.show_name = show_name

    @commands.command()
    async def password(self, ctx, length: typing.Optional[int] = 8):
        """Generates a password and sends it to you in DMs!"""

        url = f"http://kal-byte.co.uk:4040/passwordgen/{length}"
        async with self.bot.session.get(url) as r:
            if r.status != 200:
                return await ctx.send(f"The API returned a {r.status} status.")
            data = await r.json()
            password = discord.utils.escape_markdown(data["data"])
            try:
                if len(password) > 2000:
                    return await ctx.send("That password is too long...")
                    
                await ctx.author.send(
                    "Here is your newly generated password:\n"
                    f"{password}"
                )
                await ctx.send("Check your DMs to get your generated password.")
            except discord.Forbidden:
                await ctx.send(
                    "I could not send the password to you. "
                    "Please make sure you can recieve DMs from the bot."
                )

    @commands.command(hidden=True, aliases=["hello"])
    async def hey(self, ctx):
        """Displays the bots introduction."""

        await ctx.send(
            f"Hello {ctx.author.mention} I am a bot created by kal#1806 made for general purpose, utilities and moderation."
        )

    @commands.command()
    async def privacy(self, ctx):
        """Sends the bots privacy policy via dms."""

        message = """What information is stored?
- Server ID's, Channel ID's, User ID's will be saved for the use of features such as Mutes, verification etc.

Why this information is stored and how we use it.
- This information is stored to keep the bot with the most up to date info that allows it to keep running it's correct service.
- The mute data is stored temporarily and is used to check when the mute is supposed to end, or if you're supposed to be muted if you join or leave.

Who gets this data?
- The bot developer(s).
- If you're muted then your mute data will be formed into something readable by the `Moderations` command and this can be seen by any server staff member.

How to remove your data.
- If you'd like to get your servers data out of the bot then please either use the correct commands if given an option or contact the bot developer (kal#1806) for more information."""

        await ctx.author.send(message)

    @commands.command()
    async def suggest(self, ctx, *, suggestion: str):
        """Send a suggestion to the bot developer."""

        msg = f"**Suggestion from {ctx.author} ({ctx.author.id}) at {ctx.message.created_at}**\n{suggestion}"
        await ctx.bot.get_channel(710978375426244729).send(msg)
        await ctx.thumbsup()

    @commands.command()
    async def invite(self, ctx):
        """Sends an link to invite the bot to your server."""

        bot_invite = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot"

        embed = utils.embed_message(
            title="Invite the bot to your server here!", url=bot_invite
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def support(self, ctx):
        """Gives a link to the support server."""

        await ctx.send(
            "If you need help with the bot please join the support server:\n"
            + f"{config('SUPPORT_LINK')}"
        )

    @commands.command()
    async def uptime(self, ctx):
        """Get the bots uptime."""

        await ctx.send(f"Uptime: {self.bot.get_uptime()}")

    @commands.command(aliases=["git", "code", "src"])
    async def github(self, ctx):
        """Sends the bots github repo"""

        await ctx.send(
            "Heres my source code:\n"
            f"{config('GITHUB_LINK')}"
        )


def setup(bot):
    bot.add_cog(Misc(bot, "💫 Misc"))
