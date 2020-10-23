import logging

logging.basicConfig(level=logging.INFO)

import asyncio
import os
import logging
import time
import dbl
from discord.flags import MemberCacheFlags
import ksoftapi

from decouple import config
from discord import Game, Status, AllowedMentions, Intents
from discord.ext import commands

from utils import utils
from utils.CustomBot import MyBot

# logger = logging.getLogger("commands")
# logger.setLevel(logging.DEBUG)
# filename = "logs/bot_commands_" + time.ctime()[4:16].replace(":", ".") + ".log"
# filename = filename.replace(" ", "_")
# handler = logging.FileHandler(filename="debug_discord.log", encoding="utf-8", mode="w")
# handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
# logger.addHandler(handler)

new_guilds = False

my_mentions = AllowedMentions(everyone=False, roles=False)

my_intents = Intents(
    guilds=True, members=True, bans=True, messages=True, reactions=True
)

stuff_to_cache = MemberCacheFlags.from_intents(my_intents)

bot = MyBot(
    status=Status.dnd,
    activity=Game(name="Connecting..."),  # Connecting to the gateway :thonk:
    case_insensitive=True,
    max_messages=100,  # Minimum we can cache, just drops resource usage.
    allowed_mentions=my_mentions,
    intents=my_intents,
    member_cache_flags=stuff_to_cache,
    chunk_guilds_at_startup=True,
)

bot.version = "2020.10.16"
bot.description = (
    "A general purpose discord bot that provides a lot of utilities and such to use."
)
bot.owner_id = 671777334906454026
bot.owner_ids = {671777334906454026}  # Put your ID here, maybe some other peoples

# bot.kclient = ksoftapi.Client(config("KSOFT_API"))
# bot.translate_api = translator.Translator()
# bot.vac_api = vacefron.Client()
# bot.dagpi = asyncdagpi.Client(config("DAGPI"))
# bot.cse = async_cse.Search(config("GOOGLE_CSE"))

bot.exts = [
    "cogs.Developer",
    "cogs.Meta",
    "cogs.Management",
    "cogs.Moderation",
    "cogs.Fun",
    "cogs.Misc",
]

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

# Commands
# for file in os.listdir("./cogs"):
#     if file.endswith(".py"):
#         bot.load_extension(f"cogs.{file[:-3]}")
#         logging.info(f"-> [MODULE] {file[:-3]} loaded.")

cogs = [
    "cogs.custom.MotherRussia",
    "cogs.custom.SCrib",
    "cogs.custom.antinuke",
    "cogs.custom.UserRequests",
    "jishaku",
]

for cog in cogs:
    bot.load_extension(cog)
    logging.info(f"-> [MODULE] {cog[5:]} loaded.")

for ext in bot.exts:
    bot.load_extension(ext)
    logging.info(f"-> [MODULE] {ext[5:]} loaded.")

# Utilities
for file in os.listdir("./cogs/utils"):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.utils.{file[:-3]}")
        logging.info(f"-> [MODULE] {file[:-3]} loaded.")

"""
Y'know if you have a lot of cogs, it's just easier loading them this way.
"""

# Events, I keep them in a separate folder because well, it's just personal preference
for file in os.listdir("./events"):
    if file.endswith(".py"):
        bot.load_extension(f"events.{file[:-3]}")
        logging.info(f"-> [EVENT] {file[:-3]} loaded.")


@bot.event
async def on_ready():
    global new_guilds
    await bot.change_presence(
        activity=Game(name=config("BOT_STATUS"))
    )  # Set the status
    logging.info(f"Logged in as -> {bot.user.name}")  # Basic info on the bot @ startup
    logging.info(f"Client ID -> {bot.user.id}")
    logging.info(f"Guild Count -> {len(bot.guilds)}")

    # Makes sure that all the guilds the bot is in are registered in the database
    # This may need to be used IF the bot is offline and gets added to new servers
    for guild in bot.guilds:
        get_guild = await bot.pool.fetchval(
            "SELECT guild_id FROM guild_settings WHERE guild_id = $1", guild.id
        )
        if get_guild is None:
            new_guilds = True
            await bot.pool.execute(
                "INSERT INTO guild_settings(guild_id) VALUES($1)", guild.id
            )

    if (
        new_guilds
    ):  # Just tell me if there's any guilds that got added if the bot was down
        logging.info("-> Added new guild(s) to database.")


bot.run(config("BOT_TOKEN"))
