import discord
import prettify_exceptions
from decouple import config
from discord.ext import commands
from discord.ext.commands import Cog

from utils import utils
from utils.custombot import MyBot
from utils.embed import Embed

import typing

"""Pretty much from here:
    https://github.com/4Kaylum/DiscordpyBotBase/blob/master/cogs/error_handler.py"""

# noinspection PyRedundantParentheses


class ErrorHandler(Cog):
    def __init__(self, bot):
        self.bot: MyBot = bot

    async def send_to_ctx_or_author(
        self, ctx, text: str = None, *args, **kwargs
    ) -> typing.Optional[discord.Message]:
        """Tries to send the given text to ctx, but failing that, tries to send it to the author
        instead. If it fails that too, it just stays silent."""

        try:
            return await ctx.reply(text, *args, **kwargs)
        except discord.Forbidden:
            try:
                return await ctx.author.send(text, *args, **kwargs)
            except discord.Forbidden:
                pass
        except discord.NotFound:
            pass
        return None

    async def send_error(self, ctx, error):
        error_log_channel = self.bot.get_channel(768497134751186954)
        embed = Embed.error(
            title="Something went wrong...",
            description=f"```py\nAn Error Occurred:\n{error}\n```",
        )
        embed.set_author(
            name=f"{ctx.author} | {ctx.author.id}", icon_url=ctx.author.avatar_url
        )
        if ctx.guild:
            cmd = (
                "None"
                if isinstance(ctx.command, type(None))
                else ctx.command.qualified_name
            )
            embed.set_thumbnail(url=ctx.guild.icon_url_as(size=512))
            embed.add_field(
                name="Key Information:",
                value=f"Channel: {ctx.channel} {ctx.channel.id}\n"
                f"Guild: {ctx.guild} {ctx.guild.id}\n"
                f"Command: {cmd}\n"
                f"Message Content: {ctx.message.content}",
            )

        await error_log_channel.send(embed=embed)

    @Cog.listener()
    async def on_command_error(self, ctx, error):
        ignored_errors = (
            commands.CommandNotFound,
        )

        error = getattr(error, "original", error)

        if isinstance(error, ignored_errors):
            return

        setattr(
            ctx, "original_author_id", getattr(
                ctx, "original_author_id", ctx.author.id)
        )
        owner_reinvoke_errors = (
            commands.MissingAnyRole,
            commands.MissingPermissions,
            commands.MissingRole,
            commands.CommandOnCooldown,
            commands.DisabledCommand,
        )

        if ctx.original_author_id in self.bot.owner_ids and isinstance(
            error, owner_reinvoke_errors
        ):
            return await ctx.reinvoke()

        elif isinstance(error, commands.MaxConcurrencyReached):
            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(ctx,
                                  description=f"{error}"),
                delete_after=5.0,
            )

        # Command failed global check
        elif isinstance(error, commands.CheckFailure):
            if self.bot.maintenance_mode:
                fmt = ("The developer has currently put the bot into maintenance mode, this could be due to a severe "
                       "bug or something that requires the bot to be contained. The bots functionality "
                       "outside of commands will still work though, sorry for the inconvenience.\n"
                       f"For more updates you may join the support server: {config('SUPPORT_LINK')}")
                embed = Embed.default(ctx,
                                      title="\N{WARNING SIGN} | Maintenance Mode",
                                      description=fmt)
                return await ctx.send(embed=embed)

            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description=f"{error}"
                )
            )

        # If the emoji couldn't be converted
        elif isinstance(error, commands.PartialEmojiConversionFailure):
            if ctx.command.name == "emoji":
                return

            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description=f"{error}"
                ),
                delete_after=5.0,
            )

        # Command is on Cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description=f"This command is on cooldown. **`{int(error.retry_after)}` seconds**"
                ),
                delete_after=5.0,
            )

        # Missing argument
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send_help(ctx.command)

        # Missing Permissions
        elif isinstance(error, commands.MissingPermissions):
            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description=f"You're missing the required permission: `{error.missing_perms[0]}`"
                ),
            )

        # Bad Argument passed
        elif isinstance(error, commands.BadArgument):
            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description=f"{error}"
                ),
            )

        # Missing Permissions
        elif isinstance(error, commands.BotMissingPermissions):
            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description=f"I'm missing the required permission: `{error.missing_perms[0]}`"
                ),
            )

        # User who invoked command is not owner
        elif isinstance(error, commands.NotOwner):
            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description="You must be the owner of the bot to run this."
                ),
            )

        # Role was not found
        elif isinstance(error, commands.RoleNotFound):
            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description=f"{error}"
                ),
            )

        # Custom exception
        elif isinstance(error, utils.MemberIsStaff):
            return await self.send_to_ctx_or_author(
                ctx,
                embed=Embed.error(
                    description=f"{error}"
                ),
            )

        prettify_exceptions.DefaultFormatter().theme['_ansi_enabled'] = False
        tb =  (
            ''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__))
        )

        await self.send_error(ctx, tb)
        await self.send_to_ctx_or_author(ctx, embed=Embed.error(
            title="Uhoh an error has occurred...",
            description=(
                "Here's some details on it: ```py\n"
                f"{tb}```"
            )
        ))
        raise error


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
