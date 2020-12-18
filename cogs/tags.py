import uuid

import KalDiscordUtils
from discord.ext import commands, menus
import discord

import typing

import utils


class TagsListPageSource(menus.ListPageSource):
    def __init__(self, username: str, all_tags: list, *, per_page: int = 10):
        super().__init__(all_tags, per_page=per_page)

        self.username: str = username

    async def format_page(self, menu: menus.Menu, all_tags: list):
        embed = KalDiscordUtils.Embed.default(menu.ctx)
        embed.title = f'{self.username}\'s tags'
        embed.description = "\n".join(all_tags)

        return embed


class TagContent(commands.Converter):
    def __init__(self, tag_type: typing.Literal['title', 'content']):
        self.tag_type: str = tag_type.lower()

    async def convert(self, ctx, argument):
        if self.tag_type == 'title':
            reserved_names: list = ['create', 'make', 'add', 'list', 'delete']
            if len(argument) > 32:
                raise commands.BadArgument(
                    'The title must not be longer than 32 characters.')
            if argument in reserved_names:
                raise commands.BadArgument('That tag name is reserved.')
            else:
                return argument

        if self.tag_type == 'content':
            if len(argument) > 2016:
                raise commands.BadArgument(
                    'The content must not be longer than 2016 characters.')
            else:
                return argument
        else:
            raise Exception(
                'How the fuck did you fuck up this bad and not get "title" or "content"?')


class Tags(utils.BaseCog, name="tags"):
    def __init__(self, bot: utils.MyBot, show_name: str):
        self.bot: utils.MyBot = bot
        self.show_name: str = show_name

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: utils.CustomContext):
        """The base command for everything to do with tags.
        Note: These tags are not global and only stay within the server they're created in."""

        await ctx.send_help(ctx.command)

    @tag.command(name="list")
    async def tag_list(self, ctx: utils.CustomContext, *, user: typing.Optional[discord.Member]):
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
            all_tags.append(f'{i} - {tag["title"]}')

        source = TagsListPageSource(user.name, all_tags)
        menu = utils.KalPages(source)

        await menu.start(ctx)

    @tag.command(name='create', aliases=['make', 'add'])
    async def tag_create(self,
                         ctx: utils.CustomContext,
                         tag_name: TagContent('title'),
                         *, tag_content: TagContent('content')):
        """Creates a tag with a given name and gives it the given content.
        Example: `{prefix}tag create "kal is the best" this is a very true statement.`"""

        tag_id = uuid.uuid4()


def setup(bot):
    bot.add_cog(Tags(bot, '\N{NOTEBOOK WITH DECORATIVE COVER} Tags'))
