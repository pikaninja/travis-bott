import discord
from discord.ext.commands import Cog, command, cooldown, BucketType
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
    async def on_raw_reaction_add(self, payload):
        # Human Verification
        if payload.guild_id != self.id:
            return

        if payload.member.bot:
            return

        if payload.emoji.name != "\N{OK HAND SIGN}":
            return

        if self.message_id != payload.message_id:
            return

        member = payload.member

        guild = await self.bot.fetch_guild(guild_id=payload.guild_id)
        remove_role = get(guild.roles, id=self.remove_role_id)
        lawyer_role = get(guild.roles, id=self.lawyer_role_id)
        await member.remove_roles(remove_role, reason="Human Verification")
        await member.add_roles(lawyer_role, reason="Human Verification")
        # Human Verification END

    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == self.id:
            # Nuke Bot Protection
            if member.bot:
                return await member.kick(reason="No fuckin bots")

            await member.edit(nick=member.name + " 🎄")
            # Nuke bot Protection End

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

    @command(name="petrat")
    async def mr_petrat(self, ctx):
        if ctx.guild.id != self.id:
            return
        role = get(ctx.guild.roles, id=735753567914426418)
        if role in ctx.author.roles:
            await ctx.author.edit(nick="El " + ctx.author.display_name + " 🐀")

    @command(name="nuke")
    async def mr_nuke(self, ctx):
        if ctx.guild.id not in [self.id, 779233819923709963]:
            return
        await ctx.send(
            "'Platform is a nuke bot guys!' or something along those lines - Arooster 2k20"
        )

    # @command(name="kal")
    # @cooldown(1, 3600, BucketType.member)
    # async def mr_kal(self, ctx):
    #     if ctx.guild.id != self.id: return
    #     await ctx.send(f"<@671777334906454026>")


def setup(bot):
    bot.add_cog(MotherRussia(bot))
