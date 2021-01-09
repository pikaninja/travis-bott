"""
Initializes the bot and sets up some other things.
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
import utils
import os
from utils.custombot import MyBot
from discord import Game, Status, AllowedMentions, Intents
from discord.ext.ipc import Server
from discord.flags import MemberCacheFlags

logger = utils.create_logger("travis-bott", logging.INFO)

my_mentions = AllowedMentions(everyone=False, roles=False)

my_intents = Intents.default()
my_intents.members = True

stuff_to_cache = MemberCacheFlags.from_intents(my_intents)

bot = MyBot(
    status=Status.dnd,
    activity=Game(name="Connecting..."),  # Connecting to the gateway :thonk:
    case_insensitive=True,
    max_messages=1000,
    allowed_mentions=my_mentions,
    intents=my_intents,
    member_cache_flags=stuff_to_cache,
    chunk_guilds_at_startup=False,
)
bot.ipc = Server(bot, "0.0.0.0", 8765, bot.from_config("secret_key"))

bot.version = "But Better"
bot.description = (
    "A general purpose discord bot that provides a lot of utilities and such to use."
)
bot.owner_ids = {671777334906454026,
                 200301688056315911}

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

cogs = [
    "cogs.developer",
    "cogs.meta",
    "cogs.management",
    "cogs.moderation",
    "cogs.fun",
    "cogs.imagemanipulation",
    "cogs.misc",
    "cogs.jishaku",
    "cogs.beta",
    "cogs.topgg",
    "cogs.custom.motherrussia",
    "cogs.custom.scrib",
    "cogs.custom.antinuke",
    "cogs.custom.userrequests",
]

for cog in cogs:
    try:
        bot.load_extension(cog)
        logger.info(
            f"-> [MODULE] {cog[5:] if cog.startswith('cog') else cog} loaded.")
    except Exception as e:
        logger.critical(f"{type(e).__name__} - {e}")

# Utilities
for file in os.listdir("./cogs/utils"):
    if file.endswith(".py"):
        try:
            bot.load_extension(f"cogs.utils.{file[:-3]}")
            logger.info(f"-> [MODULE] {file[:-3]} loaded.")
        except Exception as e:
            logger.critical(f"{type(e).__name__} - {e}")


@bot.event
async def on_ready():
    logger.info(f"Logged in as -> {bot.user.name}")
    logger.info(f"Client ID -> {bot.user.id}")
    logger.info(f"Guild Count -> {len(bot.guilds)}")

bot.ipc.start()

token = bot.bot_token_for(
    "main") if os.name != "nt" else bot.bot_token_for("beta")
bot.run(token)
