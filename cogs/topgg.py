"""
Task to automatically post the programs server count.
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

import logging

from decouple import config
from discord.ext import tasks

import utils


class TopGG(utils.BaseCog):
    def __init__(self, bot):
        self.bot: utils.MyBot = bot
        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

        self.dbl_token = config("TOP_GG_API")
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    @tasks.loop(minutes=30)
    async def update_stats(self):
        await self.bot.wait_until_ready()
        if self.bot.user.id != 706530005169209386:
            return

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
            self.logger.info("Posted server count")
        except Exception as e:
            fmt = f"Error attempting to post guild count: {type(e).__name__} - {e}"
            await self.bot.error_webhook.send(content=fmt)


def setup(bot):
    bot.add_cog(TopGG(bot))
