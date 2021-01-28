from discord.ext import commands


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles = {
            804128843446616095: 804129377553874975
        }

    async def cog_check(self, ctx):
        return ctx.guild.id == 710978374746767440

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id not in self.reaction_roles.keys():
            return

        guild = self.bot.get_guild(710978374746767440)
        role = guild.get_role(self.reaction_roles[payload.message_id])
        await payload.member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id not in self.reaction_roles.keys():
            return

        guild = self.bot.get_guild(710978374746767440)
        role = guild.get_role(self.reaction_roles[payload.message_id])
        member = guild.get_member(payload.user_id)
        await member.remove_roles(role)


def setup(bot):
    bot.add_cog(Support(bot))