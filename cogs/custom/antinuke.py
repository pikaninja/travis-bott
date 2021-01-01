"""
Anti nuke event for the program.
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

from discord.ext.commands import Cog


class AntiNuke(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot
        self.id = [
            753723391923716126,
            695605597080649799,
            460975044139679746,
            779233819923709963,
            530497097095446538,
            781859307100569631,
            769432780278071296,
        ]

    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id in self.id:
            if member.bot:
                await member.kick(reason="No fuckin bots")


def setup(bot):
    bot.add_cog(AntiNuke(bot))
