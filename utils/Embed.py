import discord
import datetime


class Embed(discord.Embed):
    def __init__(self, colour=0x2150c1, timestamp=None, **kwargs):
        super(Embed, self).__init__(
            colour=colour,
            timestamp=timestamp or datetime.datetime.utcnow(),
            **kwargs
        )

    @classmethod
    def default(cls, ctx, **kwargs):
        instance = cls(**kwargs)
        instance.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)
        return instance

    @classmethod
    def error(cls, colour=0xf5291b, **kwargs):
        return cls(colour=colour, **kwargs)

    @classmethod
    def warning(cls, colour=0xf55c1b, **kwargs):
        return cls(colour=colour, **kwargs)
