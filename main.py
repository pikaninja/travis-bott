import os
import logging
import time

from decouple import config
from discord import Game, Status, AllowedMentions
from discord.ext import commands

from utils.CustomHelp import CustomHelp

from utils import db, utils
from utils.CustomBot import MyBot

# logger = logging.getLogger("commands")
# logger.setLevel(logging.DEBUG)
# filename = "logs/bot_commands_" + time.ctime()[4:16].replace(":", ".") + ".log"
# filename = filename.replace(" ", "_")
# handler = logging.FileHandler(filename="debug_discord.log", encoding="utf-8", mode="w")
# handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
# logger.addHandler(handler)

new_guilds = False

bot = MyBot(
    status=Status.dnd,
    activity=Game(name="Connecting..."), # Connecting to the gateway :thonk:
    case_insensitive=True,
    max_messages=100, # Minimum we can cache, just drops resource usage.
    allowed_mentions=AllowedMentions(everyone=False, roles=False)
)
bot.description = "A general purpose discord bot that provides a lot of utilities and such to use."
bot.owner_id = 671777334906454026
bot.owner_ids = {671777334906454026} # Put your ID here, maybe some other peoples

# Commands
# for file in os.listdir("./cogs"):
#     if file.endswith(".py"):
#         bot.load_extension(f"cogs.{file[:-3]}")
#         utils.log(f"-> [MODULE] {file[:-3]} loaded.")

cogs = [
    "cogs.Developer",
    "cogs.General",
    "cogs.Management",
    "cogs.Moderation",
    "cogs.Fun",
    "cogs.Utility",
    "cogs.Misc",
    "cogs.custom.MotherRussia",
    "cogs.custom.SCrib",
    "cogs.custom.Succ",
    "cogs.custom.UserRequests"
]

for cog in cogs:
    bot.load_extension(cog)
    utils.log(f"-> [MODULE] {cog[5:]} loaded.")

# Utilities
for file in os.listdir("./cogs/utils"):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.utils.{file[:-3]}")
        utils.log(f"-> [MODULE] {file[:-3]} loaded.")

'''
Y'know if you have a lot of cogs, it's just easier loading them this way.
'''

# Events, I keep them in a separate folder because well, it's just personal preference
for file in os.listdir("./events"):
    if file.endswith(".py"):
        bot.load_extension(f"events.{file[:-3]}")
        utils.log(f"-> [EVENT] {file[:-3]} loaded.")

@bot.event
async def on_ready():
    global new_guilds
    await db.script_exec("./data/db/build.sql") # Execute the build script
    await bot.change_presence(activity=Game(name=config("BOT_STATUS"))) # Set the status
    utils.log(f"Logged in as -> {bot.user.name}") # Basic info on the bot @ startup
    utils.log(f"Client ID -> {bot.user.id}")
    utils.log(f"Guild Count -> {len(bot.guilds)}")

    # Makes sure that all the guilds the bot is in are registered in the database
    # This may need to be used IF the bot is offline and gets added to new servers
    for guild in bot.guilds:
        get_guild = await db.field(f"SELECT guild_id FROM guild_settings WHERE guild_id = ?", guild.id)
        if get_guild is None:
            new_guilds = True
            await db.execute(f"INSERT INTO guild_settings(guild_id) VALUES(?)", guild.id)
            await db.commit()
    
    if new_guilds: # Just tell me if there's any guilds that got added if the bot was down
        utils.log("-> Added new guild(s) to database.")

bot.run(config("BOT_TOKEN"))
