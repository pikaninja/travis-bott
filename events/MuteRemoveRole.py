
from discord.ext.commands import Cog
from discord.utils import get

from utils import db


class MuteRemove(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_member_update(self, before, after):
        # Muted People
        check_guild_in_db = await db.field(f"SELECT guild_id FROM guild_mutes WHERE guild_id = ?", before.guild.id)
        is_user_muted = await db.field(f"SELECT member_id FROM guild_mutes WHERE guild_id = ? AND member_id = ?", before.guild.id, before.id)

        if check_guild_in_db is None:
            return

        if is_user_muted is None:
            return

        role_id = await db.field(f"SELECT mute_role_id FROM guild_settings WHERE guild_id = ?", before.guild.id)
        role = before.guild.get_role(role_id)

        if role in before.roles and role not in after.roles:
            await db.execute(f"DELETE FROM guild_mutes WHERE guild_id = ? AND member_id = ?", before.guild.id, before.id)
            await db.commit()

def setup(bot):
    bot.add_cog(MuteRemove(bot))