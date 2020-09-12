import discord
from discord.ext import commands
from discord.ext.commands import Cog

from utils import utils

import typing

# noinspection PyRedundantParentheses
class ErrorHandler(Cog):
    def __init__(self, bot):
        self.bot = bot

    """Pretty much from here:
    https://github.com/4Kaylum/DiscordpyBotBase/blob/master/cogs/error_handler.py"""

    async def send_to_ctx_or_author(self, ctx, text: str = None) -> typing.Optional[discord.Message]:
        """Tries to send the given text to ctx, but failing that, tries to send it to the author
        instead. If it fails that too, it just stays silent."""

        try:
            return await ctx.send(text)
        except discord.Forbidden:
            try:
                return await ctx.author.send(text)
            except discord.Forbidden:
                pass
        except discord.NotFound:
            pass
        return None

    @Cog.listener()
    async def on_command_error(self, ctx, error):
        ignored_errors = (commands.CommandNotFound)

        if isinstance(error, ignored_errors):
            return

        setattr(ctx, "original_author_id", getattr(ctx, "original_author_id", ctx.author.id))
        owner_reinvoke_errors = (
            commands.MissingAnyRole, commands.MissingPermissions,
            commands.MissingRole, commands.CommandOnCooldown, commands.DisabledCommand
        )

        if ctx.original_author_id in self.bot.owner_ids and isinstance(error, owner_reinvoke_errors):
            return await ctx.reinvoke()

        # Command is on Cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            return await self.send_to_ctx_or_author(ctx, f"This command is on cooldown. **`{int(error.retry_after)}` seconds**")

        # Missing argument
        elif isinstance(error, commands.MissingRequiredArgument):
            # message = utils.embed_message(title="Missing Argument.",
            #                               message=f"You're missing the required argument: `{error.param.name}`",
            #                               footer_icon=self.bot.user.avatar_url)
            # return await ctx.send(embed=message, delete_after=2)
            return await ctx.send_help(ctx.command)

        # Missing Permissions
        elif isinstance(error, commands.MissingPermissions):
            return await self.send_to_ctx_or_author(ctx, f"You're missing the required permission: `{error.missing_perms[0]}`")

        # Missing Permissions
        elif isinstance(error, commands.BotMissingPermissions):
            return await self.send_to_ctx_or_author(ctx, f"Platform is missing the required permission: `{error.missing_perms[0]}`")

        # Discord Forbidden, usually if bot doesn't have permissions
        elif isinstance(error, discord.Forbidden):
            return await self.send_to_ctx_or_author(ctx, f"I was unable to complete this action, this is most likely due to permissions.")

        # User who invoked command is not owner
        elif isinstance(error, commands.NotOwner):
            return await self.send_to_ctx_or_author(ctx, f"You must be the owner of the bot to run this.")
        
        raise error

def setup(bot):
    bot.add_cog(ErrorHandler(bot))