CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT NOT NULL,
    guild_prefix TEXT NOT NULL DEFAULT "tb!",
    mute_role_id BIGINT,
    log_channel BIGINT,
    PRIMARY KEY (guild_id)
);