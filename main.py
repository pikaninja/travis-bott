import datetime

from utils.CustomBot import MyBot
from discord import Game, Status, AllowedMentions, Intents
from decouple import config
from discord.flags import MemberCacheFlags
import os
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    filename="./logs/discord.log",
    filemode="w"
)

log = logging.getLogger(__name__)
handler = RotatingFileHandler("./logs/discord.log",
                              maxBytes=5242880,  # 5 Megabytes
                              backupCount=1)
log.addHandler(handler)

new_guilds = False

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

bot.version = "But Better"
bot.description = (
    "A general purpose discord bot that provides a lot of utilities and such to use."
)
bot.owner_ids = {671777334906454026,
                 200301688056315911}

bot.exts = [
    "cogs.Developer",
    "cogs.Meta",
    "cogs.Management",
    "cogs.Moderation",
    "cogs.Fun",
    "cogs.ImageManipulation",
    "cogs.Misc",
]

if datetime.datetime.utcnow().month == 11 or datetime.datetime.utcnow().month == 12:
    bot.exts.append("cogs.Christmas")

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
    log.info(f"-> [MODULE] {cog[5:]} loaded.")

for ext in bot.exts:
    bot.load_extension(ext)
    log.info(f"-> [MODULE] {ext[5:]} loaded.")

# Utilities
for file in os.listdir("./cogs/utils"):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.utils.{file[:-3]}")
        log.info(f"-> [MODULE] {file[:-3]} loaded.")


@bot.event
async def on_ready():
    global new_guilds
    await bot.change_presence(
        activity=Game(name=config("BOT_STATUS"))
    )  # Set the status
    # Basic info on the bot @ startup
    log.info(f"Logged in as -> {bot.user.name}")
    log.info(f"Client ID -> {bot.user.id}")
    log.info(f"Guild Count -> {len(bot.guilds)}")

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
        log.info("-> Added new guild(s) to database.")


bot.run(config("BOT_TOKEN"))
