import dbl
from decouple import config
from discord.ext import tasks

import utils


class TopGG(utils.BaseCog):
    def __init__(self, bot):
        self.bot: utils.MyBot = bot
        self.dbl_token = config("TOP_GG_API")
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    @tasks.loop(minutes=30)
    async def update_stats(self):
        await self.bot.wait_until_ready()

        try:
            server_count = len(self.bot.guilds)
            url = "https://top.gg/api/bots/706530005169209386/stats"
            headers = {
                "Authorization": self.dbl_token
            }
            data = {
                "server_count": server_count
            }
            await self.bot.session.post(url=url,
                                        headers=headers,
                                        data=data)
        except Exception as e:
            fmt = f"Error attempting to post guild count: {type(e).__name__} - {e}"
            await self.bot.error_webhook.send(content=fmt)


def setup(bot):
    bot.add_cog(TopGG(bot))
