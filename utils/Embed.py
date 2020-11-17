import discord
import datetime


class Embed(discord.Embed):
    def __init__(self, colour=0xe0651d, timestamp=None, **kwargs):
        super(Embed, self).__init__(
            colour=colour,
            timestamp=timestamp or datetime.datetime.utcnow(),
            **kwargs
        )

    @classmethod
    def default(self, ctx, **kwargs):
        instance = self(**kwargs)
        instance.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)
        return instance