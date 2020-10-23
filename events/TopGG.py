from discord.ext import commands, tasks
from decouple import config
import dbl
import time


class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.token = config("TOP_GG_API")
        self.dblpy = dbl.DBLClient(self.bot, self.token)

    @tasks.loop(minutes=30.0)
    async def update_stats(self):
        """Function runs every 30 minutes to update server count statistics."""

        try:
            await self.dblpy.post_guild_count()
        except Exception as e:
            print(f"Failed to post server count\n{type(e).__name__}: {e}")

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        print(data)
        user = data["user"]
        await self.bot.pool.execute(
            "INSERT INTO bot_votes(user_id, time_voted) VALUES($1, $2)",
            user,
            int(time.time()),
        )


def setup(bot):
    bot.add_cog(TopGG(bot))
