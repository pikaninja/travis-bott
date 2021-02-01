"""
Commands for users to create custom tags for other users to use.
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

import uuid
import logging
import discord
import utils
import typing as t
from discord.ext import commands, menus


class TagsListPageSource(menus.ListPageSource):
    def __init__(self, username: str, all_tags: list, *, per_page: int = 10):
        super().__init__(all_tags, per_page=per_page)

        self.username: str = username

    async def format_page(self, menu: menus.Menu, all_tags: list):
        embed = menu.ctx.bot.embed(menu.ctx)
        embed.title = f'{self.username}\'s tags'
        embed.description = "\n".join(all_tags)

        return embed


class TagTitle(commands.Converter):
    async def convert(self, ctx: utils.CustomContext, argument: str):
        reserved_names: list = ['create', 'make', 'add', 'list', 'delete']
        if len(argument) > 32:
            raise commands.BadArgument(
                'The title must not be longer than 32 characters.')
        if argument in reserved_names:
            raise commands.BadArgument('That tag name is reserved.')
        else:
            return argument


class Tags(commands.Cog, name="tags"):
    def __init__(self, bot: utils.MyBot):
        self.bot: utils.MyBot = bot
        self.show_name: str = "\N{NOTEBOOK WITH DECORATIVE COVER} Tags"

        self.logger = utils.create_logger(
            self.__class__.__name__, logging.INFO)

    async def cog_check(self, ctx: utils.CustomContext):
        return hasattr(ctx, 'guild')

    def _is_privileged(self, ctx: utils.CustomContext):
        return ctx.author.guild_permissions.manage_messages

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: utils.CustomContext, tag: t.Optional[str]):
        """The base command for everything to do with tags.
        Note: These tags are not global and only stay within the server they're created in."""

        if not tag:
            return await ctx.send_help(ctx.command)

        tag = await self.bot.pool.fetchrow('SELECT * FROM tags WHERE title = $1', tag)

        if tag is None:
            raise commands.BadArgument('I could not find that tag.')

        await ctx.send(tag['content'])

    @tag.command(name="list")
    async def tag_list(self, ctx: utils.CustomContext, *, user: t.Optional[discord.Member]):
        """Gets the list of tags of a current user, or yourself.
        Example: `{prefix}tag list @kal#1806`"""

        user: discord.Member = user or ctx.author
        all_user_tags = await self.bot.pool.fetch('SELECT title FROM tags WHERE author = $1 AND guild = $2',
                                                  user.id, ctx.guild.id)

        if not all_user_tags:
            fmt: str = f'`{user.name}` has no tags to display.'
            return await ctx.send(fmt)

        all_tags = []
        for i, tag in enumerate(all_user_tags):
            all_tags.append(f'`{i + 1}`. {tag["title"]}')

        source = TagsListPageSource(user.name, all_tags)
        menu = utils.KalPages(source)

        await menu.start(ctx)

    @tag.command(name='create', aliases=['make', 'add'])
    async def tag_create(self,
                         ctx: utils.CustomContext,
                         tag_name: TagTitle,
                         *, tag_content: commands.clean_content):
        """Creates a tag with a given name and gives it the given content.
        Example: `{prefix}tag create "kal is the best" this is a very true statement.`"""

        tag_id = uuid.uuid4()
        check_sql = 'SELECT COUNT(*) FROM tags WHERE title = $1'
        count = await self.bot.pool.fetchval(check_sql, tag_name)

        if count > 0:
            raise commands.BadArgument(
                'There is already a tag with that name.')

        sql = 'INSERT INTO tags VALUES($1, $2, $3, $4, $5, $6)'
        values = (str(tag_id), ctx.guild.id,
                  ctx.author.id, tag_name, tag_content, 0)
        await self.bot.pool.execute(sql, *values)

        await ctx.send('Successfully added that tag.')

    @tag.command(name='remove', aliases=['delete', 'del'])
    async def tag_remove(self, ctx: utils.CustomContext, *, tag_name: TagTitle):
        """Removes a given tag by it's name.
        You can only remove it if you're server staff (Manage Messages) or you own the tag."""

        tag = await self.bot.pool.fetchrow('SELECT * FROM tags WHERE title = $1', tag_name)

        if tag is None:
            raise commands.BadArgument(
                'There is no tag found that has that name.')

        if not tag['author'] == ctx.author.id or not self._is_privileged(ctx):
            raise utils.NotTagOwner(
                'You do not have sufficient permissions to remove this tag.')

        sql = 'DELETE FROM tags WHERE id = $1'
        await self.bot.pool.execute(sql, tag['id'])

        fmt = 'Successfully removed that tag.'
        await ctx.send(fmt)


def setup(bot):
    bot.add_cog(Tags(bot))
