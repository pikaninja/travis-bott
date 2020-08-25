CREATE TABLE IF NOT EXISTS guild_settings(
	guild_id INTEGER PRIMARY KEY,
	guild_prefix TEXT DEFAULT "p?",
	mute_role_id INTEGER
);
CREATE TABLE IF NOT EXISTS guild_verification(
    guild_id INTEGER PRIMARY KEY,
    message_id INTEGER,
    role_id INTEGER
);
CREATE TABLE IF NOT EXISTS guild_mutes(
    guild_id INTEGER,
    member_id INTEGER,
    end_time INTEGER
);
CREATE TABLE IF NOT EXISTS premium(
    guild_id INTEGER PRIMARY KEY,
    end_time INTEGER
);