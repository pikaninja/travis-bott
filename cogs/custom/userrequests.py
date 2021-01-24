"""
Commands provided via user requests.
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

import random
from discord.ext import commands


class UserRequests(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_nsfw()
    async def balls(self, ctx):
        """A 1 in 1000 chance to literally send balls."""

        r = random.randint(0, 1000)
        sports_balls_url = [
            "https://images-na.ssl-images-amazon.com/images/I/51pupYEB7aL._AC_SX466_.jpg",
            "https://ph-test-11.slatic.net/p/d7f029135e8d1517466c12ed8cbfe01c.png_340x340q80.jpg_.webp",
            "https://ae01.alicdn.com/kf/HTB1kfN3c8yWBuNkSmFPq6xguVXam.jpg",
            "https://images-na.ssl-images-amazon.com/images/I/41MlZUa7ZXL._AC_SY400_.jpg",
        ]
        # Please don't fucking open this, it's literally a picture of a dudes testicles I swear to god, whoever is reading this do NOT do it
        literal_balls_url = "https://i.imgur.com/iCEEhX9.png"
        url = literal_balls_url if r == 1000 else random.choice(
            sports_balls_url)

        embed = self.bot.embed(ctx, title="I was paid £5 to add this")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_nsfw()
    async def cock(self, ctx):
        """A 1 in 1000 chance to send a literal cock."""

        r = random.randint(0, 1000)
        chickens_url = [
            "https://thumbs-prod.si-cdn.com/F6HW-4agcW4wegxWUxwkN3sLdkY=/fit-in/1600x0/filters:focal(451x176:452x177)/https://public-media.si-cdn.com/filer/a8/05/a80596c6-2412-497b-8f8f-e871da2fec9e/ayam-cemani-cem-046.jpg",
            "https://img.etimg.com/thumb/msid-61806530,width-640,resizemode-4,imgsize-235064/black-chicken-crosses-the-red-corridor.jpg",
            "https://cdn0.wideopencountry.com/wp-content/uploads/2017/02/Black-Chicken-793x526.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/%E0%AE%95%E0%AE%9F%E0%AE%95%E0%AF%8D%E0%AE%A8%E0%AE%BE%E0%AE%A4%E0%AF%8D_%E0%AE%9A%E0%AF%87%E0%AE%B5%E0%AE%B2%E0%AF%8D.jpg/1200px-%E0%AE%95%E0%AE%9F%E0%AE%95%E0%AF%8D%E0%AE%A8%E0%AE%BE%E0%AE%A4%E0%AF%8D_%E0%AE%9A%E0%AF%87%E0%AE%B5%E0%AE%B2%E0%AF%8D.jpg",
        ]
        # Ok, I keep getting paid to add this shit, like a 1 in 1000 chance of seeing a cock? Yall are wild lmfao ok but seriously £7.50 is £7.50
        literal_cock_url = "https://www.porn18sex.com/uploads/1img_1529100956_95794.jpg"
        url = literal_cock_url if r == 1000 else random.choice(chickens_url)

        embed = self.bot.embed(ctx, title="I was paid £2.50 to add this")
        embed.set_image(url=url)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(UserRequests(bot))
