"""
Subclassed Embed - Provides more control over embeds
Copyright (C) 2020 kal-byte

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

from discord import Embed as BaseEmbed
import datetime


class Embed(BaseEmbed):
    def __init__(self, colour=0x024136, timestamp=None, **kwargs):
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
