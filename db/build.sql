CREATE TABLE IF NOT EXISTS transactions (
    trade_details TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS todays_games (
    games_date INTEGER PRIMARY KEY,
    games TEXT
);