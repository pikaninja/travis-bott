"""
Utilities provided exclusively to the "Mothership" server.
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

import discord
from discord.ext.commands import Cog, command
from discord.utils import get


class MotherRussia(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot
        self.id = 622236317404889088
        self.gregg_id = 695656558675230780
        self.message_id = 737753235246284860
        self.remove_role_id = 737751726354071612
        self.lawyer_role_id = 735699385513541735

    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == self.id:
            if member.bot:
                return await member.kick(reason="No fuckin bots")

    @Cog.listener()
    async def on_guild_role_delete(self, role):
        if role.guild.id != self.id:
            return
        guild = role.guild
        async for entry in guild.audit_logs(
            limit=1, action=discord.AuditLogAction.role_delete
        ):
            if role.id == 735699385513541735:
                await guild.kick(entry.user, reason="Prune Protection")


def setup(bot):
    bot.add_cog(MotherRussia(bot))
