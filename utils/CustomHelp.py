from discord.ext import commands
import discord

from utils import utils
from utils import CustomContext

class CustomHelp(commands.HelpCommand):
    def __init__(self, context=CustomContext, **options):
        super().__init__(**options)

    def get_ending_note(self):
        return f"Use {self.clean_prefix}{self.invoked_with} [Command] for more info on a command."

    def get_command_signature(self, command: commands.Command):
        return f"{self.clean_prefix}{command.qualified_name} {command.signature}"
    
    async def send_bot_help(self, mapping):
        embed = utils.embed_message(title="Bot Commands")
        embed.description = self.context.bot.description + "\n\n" + \
                            "`<> | Required`\n" + \
                            "`[] | Optional`\n"

        for cog, commands in mapping.items():
            name = "No Category" if cog is None else cog.qualified_name
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                value = " ".join("`" + c.name + "`" for c in commands)
                if cog and cog.description:
                    value = f"{cog.description}\n{value}"

                embed.add_field(name=name, value=value)
        
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)
    
    async def send_cog_help(self, cog: commands.Cog):
        embed = utils.embed_message(title=f"{cog.qualified_name} Commands")
        if cog.description:
            embed.description = str(cog.description)

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=str(command.short_doc) or "...", inline=False)
        
        embed.set_footer(self.get_ending_note())
        await self.get_destination().send(embed=embed)
    
    async def send_group_help(self, group: commands.Group):
        embed = utils.embed_message(title=f"{self.clean_prefix}{group.qualified_name} {group.signature}")
        if group.help:
            aliases = f"*Aliases: {' | '.join('`' + x + '`' for x in  group.aliases)}*" if group.aliases else ""
            embed.description = str(group.help) + "\n" + aliases

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(name=self.get_command_signature(command), value=str(command.short_doc) or "...", inline=False)
            
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)
    
    send_command_help = send_group_help