"""
Commands to provide utilities to setup a server.
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

from discord.ext import commands
import discord


class CreateServer(
    commands.Cog, name="Create Server Stuff", command_attrs=dict(hidden=True)
):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="| Deletes all channels to setup !create_server")
    @commands.has_permissions(manage_guild=True)
    async def self_destruct(self, ctx):
        for channel in ctx.guild.channels:
            await channel.delete(reason="Deleting all Channels")

        await ctx.guild.create_text_channel(name="general")

    @commands.command(
        aliases=["build"],
        help="| Sets up server with roles and permissions.",
        usage="Optional: Server Name",
    )
    @commands.has_permissions(manage_guild=True)
    async def create_server(self, ctx, *, serverName: str = None):
        guild = ctx.guild

        if serverName == None:
            serverName = "Server Template"

        informationOverwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=False, add_reactions=False
            )
        }

        staffOverwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False, send_messages=False, add_reactions=False
            ),
        }

        mainOverwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                connect=True,
                speak=True,
            )
        }

        # defaultRole = discord.utils.get(guild.roles, guild.default_role)
        await guild.default_role.edit(
            permissions=discord.Permissions(
                mention_everyone=False, send_tts_messages=False
            )
        )

        await ctx.send("Server is being set up, this may take a bit.")
        await ctx.message.channel.delete(reason="Setting up server")
        await guild.edit(name="Setting up server.")

        await guild.create_category(
            name="[ Information ]", overwrites=informationOverwrites
        )
        await guild.create_category(
            name="[ Staff Channels ]", overwrites=staffOverwrites
        )
        await guild.create_category(name="[ Main Channels ]", overwrites=mainOverwrites)
        await guild.create_category(
            name="[ Community Channels ]", overwrites=mainOverwrites
        )
        await guild.create_category(
            name="[ Voice Channels ]", overwrites=mainOverwrites
        )
        await guild.create_category(name="[ Logs ]", overwrites=staffOverwrites)

        informationCategory = discord.utils.get(
            guild.categories, name="[ Information ]"
        )
        staffCategory = discord.utils.get(
            guild.categories, name="[ Staff Channels ]")
        mainCategory = discord.utils.get(
            guild.categories, name="[ Main Channels ]")
        comCategory = discord.utils.get(
            guild.categories, name="[ Community Channels ]")
        voiceCategory = discord.utils.get(
            guild.categories, name="[ Voice Channels ]")
        logsCategory = discord.utils.get(guild.categories, name="[ Logs ]")

        # Information Category
        await guild.create_text_channel(
            name="welcome",
            topic="Welcome channel, all system messages get put here.",
            category=informationCategory,
        )
        await guild.create_text_channel(
            name="rules",
            topic="Read up on the servers rules, don't break them!",
            category=informationCategory,
        )
        await guild.create_text_channel(
            name="announcements",
            topic="Server announcements will go here.",
            category=informationCategory,
        )
        await guild.create_text_channel(
            name="giveaways",
            topic="Server giveaway announcements will go here!",
            category=informationCategory,
        )

        # Staff Category
        await guild.create_text_channel(
            name="staff-announcements",
            topic="Staff announcements will go here",
            category=staffCategory,
        )
        await guild.create_text_channel(
            name="staff-rules", topic="Staff rules will go here", category=staffCategory
        )
        await guild.create_text_channel(
            name="staff-chat",
            topic="Staff chat, usually cooler than general 😎",
            category=staffCategory,
        )
        await guild.create_text_channel(
            name="staff-commands",
            topic="Staff commands go here",
            category=staffCategory,
        )
        await guild.create_text_channel(
            name="high-staff",
            topic="Staff announcements will go here",
            category=staffCategory,
        )

        # General Category
        await guild.create_text_channel(
            name="general",
            topic="General discussion, come here to make friends and such",
            category=mainCategory,
        )
        await guild.create_text_channel(
            name="commands", topic="Do your bot commands here", category=mainCategory
        )
        await guild.create_text_channel(
            name="memes", topic="Send your dankest memes here", category=mainCategory
        )

        # Community Category
        await guild.create_text_channel(
            name="face-reveal",
            topic="Get your face reveals sent here!",
            category=comCategory,
        )
        await guild.create_text_channel(
            name="self-promo", topic="Self promotion goes here", category=comCategory
        )
        await guild.create_text_channel(
            name="nsfw", topic="NSFW Content and Commands go here", category=comCategory
        )

        # Voice Category
        await guild.create_voice_channel(name="[🌍] General", category=voiceCategory)
        await guild.create_voice_channel(
            name="[15] Slots", user_limit=15, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[10] Slots", user_limit=10, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[8] Slots", user_limit=8, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[8] Slots", user_limit=8, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[5] Slots", user_limit=5, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[5] Slots", user_limit=5, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[3] Slots", user_limit=3, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[3] Slots", user_limit=3, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[2] Slots", user_limit=2, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[2] Slots", user_limit=2, category=voiceCategory
        )
        await guild.create_voice_channel(
            name="[20] Music", user_limit=20, category=voiceCategory
        )

        # Logs Category
        await guild.create_text_channel(name="staff-logs", category=logsCategory)
        await guild.create_text_channel(
            name="edited-deleted-logs", category=logsCategory
        )
        await guild.create_text_channel(name="ban-logs", category=logsCategory)
        await guild.create_text_channel(name="user-logs", category=logsCategory)

        channel = discord.utils.get(ctx.guild.channels, name="welcome")
        await ctx.guild.edit(
            system_channel=discord.utils.get(guild.channels, name="welcome")
        )
        serverInvite = await channel.create_invite(
            max_age=0, max_uses=0, temporary=False, unique=True, reason="Server Setup"
        )
        await guild.edit(
            name=serverName, verification_level=discord.VerificationLevel.medium
        )

        await channel.send(
            f"Server is done being set up.\nPermanent invite link: {serverInvite.url}"
        )


def setup(bot):
    bot.add_cog(CreateServer(bot))
