CREATE TABLE guild_settings (
    guild_id BIGINT PRIMARY KEY,
    guild_prefix VARCHAR(10) DEFAULT 'tb!',
    mute_role_id BIGINT,
    log_channel BIGINT,
    owoify BOOLEAN DEFAULT 'f'
);

CREATE TABLE guild_mutes (
    guild_id BIGINT,
    member_id BIGINT,
    end_time BIGINT
);

CREATE TABLE giveaways (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT,
    ends_at TIMESTAMP,
    role_id BIGINT
);

CREATE TABLE cookies (
    user_id BIGINT PRIMARY KEY,
    cookies INT
);

CREATE TABLE blacklist (
    id BIGINT PRIMARY KEY,
    reason TEXT
);

CREATE TABLE guild_verification (
    guild_id BIGINT PRIMARY KEY,
    message_id BIGINT,
    role_id BIGINT
);

CREATE TABLE temp_bans (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reason VARCHAR(255),
    end_time TIMESTAMP NOT NULL
);

CREATE TABLE todos (
    id INT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    task VARCHAR(100) NOT NULL
);

CREATE TABLE warns (
    id INT PRIMARY KEY,
    guild_id BIGINT,
    moderator_id BIGINT,
    offender_id BIGINT,
    reason VARCHAR(255),
    time_warned TIMESTAMP
);