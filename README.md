# BenSimmonsBot
A simple discord bot that will interact with NBA.com to pull stats and player information.
## Current features:
### Slash Commands
- [x] /player_stats (player_name) - Pulls a players overall stats from the current season.
- [x] /player_info (player_name) - Pulls general info about a specific player.
- [x] /player_log (player_name) - Pulls the last 10 games of a player and displays their Points/Assists/Rebounds.
- [x] /league_leaders - Displays the top 15 players (seemingly based on score).
### Recursive Functions
- [x] Transactions - Will pull player transaction data from NBA.com and puts it into the selected channel.
- [ ] Displays the current day's games and their scores, and keeps the message up to date. (UNTESTED)

## Install
`pip install -r requirements.txt`

Rename "example.env" to ".env" and fill in with your information.
