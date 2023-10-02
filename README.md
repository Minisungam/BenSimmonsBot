# BenSimmonsBot
A simple discord bot that will interact with NBA.com to pull stats and player information.

This is my very first python project, so it's a bit rough around the edges. I'm sure there are better ways to do some of the things I've done, but I'm still learning. I'm open to any suggestions or feedback.
## Current features:
### Slash Commands
- [x] /player_stats (player_name) - Pulls a players overall stats from the current season.
- [x] /player_info (player_name) - Pulls general info about a specific player.
- [x] /player_log (player_name) - Pulls the last 10 games of a player and displays their Points/Assists/Rebounds.
- [x] /league_leaders - Displays the top 20 players, with their points and minutes played.
- [x] /meme - Displays a random NBA meme from the top 50 hot r/Nbamemes submissions.

Only the user id specified in ".env" can do the following:
- [x] /shutdown - Safely shuts down the bot.
- [x] /transactions - Allows the user to enable or disable the transactions service.
- [x] /daily_scores - Allows the user to enable or disable the daily scores service.
- [x] /set_channels - Allows the user to choose channels to display updates from within Discord.
### Recursive Functions
- [x] Transactions - Will pull player transaction data from NBA.com and puts it into the selected channel.
- [ ] Daily Scores - Displays the current day's games and their scores, and keeps the message up to date. (UNTESTED)
### Chat Commands
- [x] !help - Displays a list of chat commands.
- [x] !roll - Rolls a random number between 1 and 10.
- [x] !abbreviations - Displays a list of NBA stat abbreviations.
## Install
`pip install -r requirements.txt`

## Setup
Rename "example.env" to ".env" and fill in with your information.

Create a new Discord application and bot at https://discord.com/developers/applications
Fill in the "BOT_TOKEN" field with your bot's token.

If you want memes to be posted, you'll need to create a Reddit application at https://www.reddit.com/prefs/apps, and fill in the "REDDIT_BOT_ID" and "REDDIT_BOT_SECRET" fields.

To get the "USER_ID" field, you'll need to enable developer mode in Discord. Go to Settings > Advanced > Developer Mode. Then right click on your name in the user list and click "Copy ID". The same goes for the all channel id fields. Right click on the channel you want to use and click "Copy ID".