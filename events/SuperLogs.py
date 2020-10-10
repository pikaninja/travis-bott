from discord.ext import commands
import discord
from utils import db, utils

class SuperLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_mod_cmd(self, action_type: str, moderator: discord.Member, user_affected: discord.Member, reason: str = None):
        """Dispatched manually by the Client.
        Contains:
        Action_type: Which is the type of action was done. This will be a string.
        Moderator: The moderator who carried out the actions, this will be of discord.Member.
        User_affected: The person who was affected within the actions, this will also be discord.Member.
        Reason: The reason provided in the action, if any. This will be a string."""

        mod_log_channel_id = await db.field("SELECT log_channel FROM guild_settings WHERE guild_id = ?", moderator.guild.id)

        if mod_log_channel_id is None:
            return
        
        log_channel = moderator.guild.get_channel(mod_log_channel_id)

        if log_channel is None:
            await db.execute("UPDATE guild_settings SET log_channel = ? WHERE guild_id = ?", None, moderator.guild.id)
            await db.commit()
            return

        embed = utils.embed_message(title=f"Super Log",
                                    message=f"{moderator.mention} ({moderator}) to {user_affected.mention} ({user_affected})\n" \
                                            f"Command: {action_type}\n" \
                                            f"Reason: {reason or 'None'}")
        embed.set_author(name=moderator.name, icon_url=moderator.avatar_url)

        await log_channel.send(embed=embed)

def setup(bot):
    bot.add_cog(SuperLogs(bot))