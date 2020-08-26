from discord.ext.commands import Cog
from discord.utils import get

from utils import db, utils


class MuteRemoveBan(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_member_ban(self, guild, member):
        # Check if Muted
        is_guild_in_db = await db.field(f"SELECT guild_id FROM guild_mutes WHERE guild_id = ?", guild.id)
        if is_guild_in_db is None:
            return

        check_if_user_muted_in_guild = await db.field(f"SELECT member_id FROM guild_mutes WHERE guild_id = ? AND member_id = ?", guild.id, member.id)
        if check_if_user_muted_in_guild is None:
            return

        await db.execute(f"DELETE FROM guild_mutes WHERE guild_id = ? AND member_id = ?", guild.id, member.id)
        await db.commit()
        # Check if Muted End

def setup(bot):
    bot.add_cog(MuteRemoveBan(bot))