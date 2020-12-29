import logging

import utils
import os

from utils.custombot import MyBot
from discord import Game, Status, AllowedMentions, Intents
from discord.ext.ipc import Server
from decouple import config
from discord.flags import MemberCacheFlags

logger = utils.create_logger("travis-bott", logging.INFO)

my_mentions = AllowedMentions(everyone=False, roles=False, users=True)

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
bot.ipc = Server(bot, "0.0.0.0", 8765, config("SECRET_KEY"))

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
    "cogs.music",
    "cogs.beta",
    "cogs.topgg",
    "cogs.custom.motherrussia",
    "cogs.custom.scrib",
    "cogs.custom.antinuke",
    "cogs.custom.userrequests",
    "jishaku",
]

for cog in cogs:
    try:
        bot.load_extension(cog)
        logger.info(f"-> [MODULE] {cog[5:]} loaded.")
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


@bot.ipc.route()
async def get_stats(data):
    return [
        f"{len(bot.guilds):,}",
        f"{sum(g.member_count for g in bot.guilds):,}",
        f"{sum(1 for c in bot.walk_commands()):,}"
    ]


@bot.ipc.route()
async def get_bot_id(data):
    user = await bot.fetch_user(data.bot_id)
    if not user.bot:
        return "706530005169209386"
    return user.id

bot.ipc.start()
bot.run(config("BOT_TOKEN"))
