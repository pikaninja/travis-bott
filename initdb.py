import config as cfg

async def run_init(bot):
    async with bot.pool.acquire() as con:
        await con.execute("""
        CREATE TABLE IF NOT EXISTS premium(
            guild_id BIGINT,
            end_time BIGINT,
            PRIMARY KEY (guild_id)
        );""")
