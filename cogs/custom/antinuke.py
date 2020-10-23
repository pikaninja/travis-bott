import discord
from discord.ext.commands import Cog, command
from discord.utils import get


class AntiNuke(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot
        self.id = [
            753723391923716126,
            695605597080649799,
            460975044139679746,
            668110509370769454,
            530497097095446538,
        ]

    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id in self.id:
            if member.bot:
                await member.kick(reason="No fuckin bots")

    @command(disabled=True)
    async def rulesting(self, ctx):
        msg = [
            "**General Rules**",
            "**1. Follow all Discord Guidelines**",
            "All of the rules outlined by Discord (link below) will be strictly enforced by the staff. No exceptions.",
            "**2. No Racial/Homophobic Slurs**",
            "We have a 0 tolerance policy for use of any derogatory terms used to attack a group of people. (Mute/Kick/Ban)",
            "**3. No harassment**",
            "Harassment of any kind is not tolerated even if it’s meant as a joke. This includes threats, wishing other members harm, encouraging harm etc. (Mute/Kick/Ban)",
            "**4. No Spamming**",
            "This includes spam text, spam tagging, spam images, waterfall text, copied messages, and copy pastas. (Warn/Mute/Kick)",
            "**5. No Doxxing**",
            "This includes leaking any personal information such as, home address, phone number, social security number, photos etc. (Kick/Ban)",
            "\n",
            "**6. Do Not Argue With Staff**",
            "Staff have the final say when it comes to server related issues/arguments and don’t have time to deal with arguments over everything. (Warn/Mute/Kick)",
            "**7. Do Not Tag Staff for No Reason**",
            "Unless it’s important and you need assistance from staff members, don’t tag them. (Warn/Mute/Kick)",
            "**8. Do Not Beg for Roles**",
            "Roles are earned not given. (Warn/Mute)",
            "**9. No Advertising**",
            "If you want to advertise/self promote use the self-promo channel. If you want to use bot commands, use the bot commands channel.",
            "\n",
            "**Content Rules**",
            "**11. Absolutely NO Gore**",
            "Posting this will result in an immediate ban and possible account suspension/account suspension.",
            "Voice Chat Rules",
            "**12. No Mic Spam**",
            "Blasting loud noises/music in vc. (Warn/Mute/Kick)",
            "**13. No VC Hopping**",
            "Self explanatory (Warn/Mute/Kick)",
            "\n",
            "**14. You must have a taggable name**",
            "\n",
            "**15. Use common sense. If you think it’s against the rules it probably is.**",
            "Failure to abide by the rules will be punished at the discretion of the staff members.",
            "\n",
            "https://discordapp.com/guidelines",
        ]
        embed = discord.Embed(
            title="Woke's Wonderland General Guidelines", description="\n".join(msg)
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(AntiNuke(bot))
