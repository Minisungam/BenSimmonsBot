import os
import responses
import aiohttp
from updaters import fetch_and_display_games, fetch_and_display_trades
import db
import asyncpraw
import asyncio
import random
from datetime import datetime
import discord
from discord import app_commands
import dotenv
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats, playergamelog, commonplayerinfo, LeagueLeaders

program_name = "BenSimmonsBot"
version = "v1.0.2"

graphic = f"""

   ___           _____                           ___       __ 
  / _ )___ ___  / __(_)_ _  __ _  ___  ___  ___ / _ )___  / /_
 / _  / -_) _ \_\ \/ /  ' \/  ' \/ _ \/ _ \(_-</ _  / _ \/ __/
/____/\__/_//_/___/_/_/_/_/_/_/_/\___/_//_/___/____/\___/\__/ 
                                                                               
Program: {program_name}
Version: {version}
"""

settings = {
    "BOT_TOKEN": "",
    "GUILD_ID": 0,
    "BOT_OWNER_ID": 0,
    "TRANSACTION_CHANNEL_ID": 0,
    "DAILY_SCORE_CHANNEL_ID": 0,
    "DEBUG_CHANNEL_ID": 0,
    "DEBUG_OUTPUT": False,
    "DAILY_SCORE_ENABLED": False,
    "DAILY_SCORE_RUNNING": False,
    "TRANSACTIONS_ENABLED": False,
    "TRANSACTIONS_RUNNING": False,
    "REDDIT_BOT_ID": "",
    "REDDIT_BOT_SECRET": ""
}

# Format the time for logging
def current_time():
    current_time = datetime.now()
    formatted_time: str = current_time.strftime("%H:%M:%S")
    return formatted_time

# Basic commands using "!" prefix
async def send_message(message, user_message, is_private):
    try:
        response = responses.get_response(user_message)
        if response is not None:
            await message.author.send(response) if is_private else await message.channel.send(response)
        else:
            return
    except Exception as e:
        print(f"[{current_time()}] Messages error: {e}")
        await message.channel.send("An error occurred. Please try again.")

def update_env_file():
    # Load environment variables
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)
    
    # Update environment variables
    dotenv.set_key(dotenv_file, "BOT_TOKEN", settings["BOT_TOKEN"])
    dotenv.set_key(dotenv_file, "GUILD_ID", str(settings["GUILD_ID"]))
    dotenv.set_key(dotenv_file, "BOT_OWNER_ID", str(settings["BOT_OWNER_ID"]))
    dotenv.set_key(dotenv_file, "TRANSACTION_CHANNEL_ID", str(settings["TRANSACTION_CHANNEL_ID"]))
    dotenv.set_key(dotenv_file, "DAILY_SCORE_CHANNEL_ID", str(settings["DAILY_SCORE_CHANNEL_ID"]))
    dotenv.set_key(dotenv_file, "DEBUG_CHANNEL_ID", str(settings["DEBUG_CHANNEL_ID"]))
    dotenv.set_key(dotenv_file, "DEBUG_OUTPUT", str(settings["DEBUG_OUTPUT"]))
    dotenv.set_key(dotenv_file, "DAILY_SCORE_ENABLED", str(settings["DAILY_SCORE_ENABLED"]))
    dotenv.set_key(dotenv_file, "TRANSACTIONS_ENABLED", str(settings["TRANSACTIONS_ENABLED"]))

# Discord bot main functionality
def run_discord_bot():
    # Load environment variables
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)
    try:
        # If bot token is not set, give up all hope
        if os.getenv('BOT_TOKEN') == "":
            raise Exception
        else:
            settings["BOT_TOKEN"]: str = os.getenv('BOT_TOKEN')
        
        settings["GUILD_ID"]: int = int(os.getenv('GUILD_ID'))
        settings["BOT_OWNER_ID"]: int = int(os.getenv('BOT_OWNER_ID'))
        settings["TRANSACTION_CHANNEL_ID"]: int = int(os.getenv('TRANSACTION_CHANNEL_ID'))
        settings["DAILY_SCORE_CHANNEL_ID"]: int = int(os.getenv('DAILY_SCORE_CHANNEL_ID'))
        settings["DEBUG_CHANNEL_ID"]: int = int(os.getenv('DEBUG_CHANNEL_ID'))
        settings["DEBUG_OUTPUT"]: bool = eval(os.getenv('DEBUG_OUTPUT'))
    except:
        print(f"[{current_time()}] Bot: Environment variables missing in .env file.")
        return
    try:
        settings["DAILY_SCORE_ENABLED"] : bool = eval(os.getenv('DAILY_SCORE_ENABLED'))
    except:
        settings["DAILY_SCORE_ENABLED"] : bool = False
        print(f"[{current_time()}] Bot: DAILY_SCORE_ENABLED setting incorrect in .env file, must be \"True\" or \"False\". Defaulting to False.")
    try:
        settings["TRANSACTIONS_ENABLED"]: bool = eval(os.getenv('TRANSACTIONS_ENABLED'))
    except:
        settings["TRANSACTIONS_ENABLED"]: bool = False
        print(f"[{current_time()}] Bot: TRANSACTIONS_ENABLED setting incorrect in .env file, must be \"True\" or \"False\". Defaulting to False.")
    try:
        settings["REDDIT_BOT_ID"]: str = os.getenv('REDDIT_BOT_ID')
        settings["REDDIT_BOT_SECRET"]: str = os.getenv('REDDIT_BOT_SECRET')
    except:
        print(f"[{current_time()}] Bot: Reddit environment variables missing in .env file.")


    # Bot setup
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    ############# Bot Events #############
    @client.event
    async def on_ready():
        global transactions_service
        global daily_scores_service

        print(graphic)

        print(f'{client.user} has connected to Discord!')
        # Daily Scores
        if settings["DAILY_SCORE_ENABLED"]:
            client.loop.create_task(fetch_and_display_games(client))
            print(f"[{current_time()}] Bot: Daily scores service started")
        else:
            print(f"[{current_time()}] Bot: Daily scores service disabled")       
        # Transactions
        if settings["TRANSACTIONS_ENABLED"]:
            client.loop.create_task(fetch_and_display_trades(client))
            print(f"[{current_time()}] Bot: Transactions service started")
        else: 
            print(f"[{current_time()}] Bot: Transactions service disabled")

        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="badly, no 3s."))
        print(f"[{current_time()}] Bot: Presence set")
        await tree.sync(guild=discord.Object(id=settings["GUILD_ID"]))
        print(f"[{current_time()}] Bot: Commands synced")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        username = str(message.author)
        user_message = str(message.content)
        channel = str(message.channel)

        print(f'{username} sent a message in {channel}: {user_message}')

        if message.guild is not None:
            await send_message(message, message.content, False)
        else:
            await send_message(message, message.content, True)

    ############# Bot Commands #############
    @tree.command(name='daily_scores', description='Enables or disables the daily scores service.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def daily_scores(interaction, enable: bool):
        if interaction.user.id == settings["BOT_OWNER_ID"]:
            if enable is True:
                response = await start_update_scores()
                await interaction.response.send_message(response, ephemeral=True)
            else:
                response = await stop_update_scores()
                await interaction.response.send_message(response, ephemeral=True)
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    @tree.command(name='transactions', description='Enables or disables the transactions service.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def transactions(interaction, enable: bool):
        if interaction.user.id == settings["BOT_OWNER_ID"]:
            if enable is True:
                response = await start_update_trades()
                await interaction.response.send_message(response, ephemeral=True)
            else:
                response = await stop_update_trades()
                await interaction.response.send_message(response, ephemeral=True)
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    @tree.command(name='set_channels', description='Set channels the bot posts in.', guild=discord.Object(id=settings["GUILD_ID"]))
    @app_commands.choices(choices=[
        app_commands.Choice(name='Daily Scores', value='daily_scores'),
        app_commands.Choice(name='Transactions', value='transactions'),
        app_commands.Choice(name='Debug', value='debug')
    ])
    async def set_channels(interaction, choices: app_commands.Choice[str]):
        if interaction.user.id == settings["BOT_OWNER_ID"]:
            if choices.value == "daily_scores":
                settings["DAILY_SCORE_CHANNEL_ID"] = interaction.channel_id
                dotenv.set_key(dotenv_file, "DAILY_SCORE_CHANNEL_ID", str(interaction.channel_id))
                await interaction.response.send_message("Daily scores channel set.", ephemeral=True)
                print(f"[{current_time()}] Bot: Daily scores channel set to {interaction.channel_id}.")
            elif choices.value == "transactions":
                settings["TRANSACTION_CHANNEL_ID"] = interaction.channel_id
                dotenv.set_key(dotenv_file, "TRANSACTION_CHANNEL_ID", str(interaction.channel_id))
                await interaction.response.send_message("Transactions channel set.", ephemeral=True)
                print(f"[{current_time()}] Bot: Transactions channel set to {interaction.channel_id}.")
            elif choices.value == "debug":
                settings["DEBUG_CHANNEL_ID"] = interaction.channel_id
                dotenv.set_key(dotenv_file, "DEBUG_CHANNEL_ID", str(interaction.channel_id))
                await interaction.response.send_message("Debug channel set.", ephemeral=True)
                print(f"[{current_time()}] Bot: Debug channel set to {interaction.channel_id}.")
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    @tree.command(name='shutdown', description='Shuts down the bot', guild=discord.Object(id=settings["GUILD_ID"]))
    async def quit_bot(interaction):
        if interaction.user.id == settings["BOT_OWNER_ID"]:
            db.commit()
            db.close()
            await interaction.response.send_message("Shutting down in 5 seconds", ephemeral=True)
            update_env_file()
            print(f"[{current_time()}] Bot: Shutting down")
            await asyncio.sleep(5)
            await client.close()
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    @tree.command(name='player_stats', description='Gets the player\'s stats for the season.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def player_stats(interaction, player_name: str):
        try:
            # Use the nba_api to search for a player
            player = players.find_players_by_full_name(player_name)
            player_id = player[0]['id']
            player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            player_data = player_info.get_data_frames()[0].iloc[0]

            # Get the player's game log
            career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
            career_stats_df = career_stats.get_data_frames()[0]

            # Get the latest year of data
            latest_year_stats = career_stats_df.iloc[-1]

            # Create the embed
            embed = discord.Embed(title=f"Player Stats for {player_data['DISPLAY_FIRST_LAST']}:", description=f"Team: `{latest_year_stats['TEAM_ABBREVIATION']}`", color=0x339cff)
            embed.set_thumbnail(url=f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png")
            embed.set_footer(text="Data provided by NBA.com", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")

            # Define a mapping for stat names to display names
            stat_name_mapping = {
                'FG_PCT': ('FG%', True),
                'FG3_PCT': ('FG3%', True),
                'FT_PCT': ('FT%', True)
            }

            # Define a list of stats to skip
            stats_to_skip = ['PLAYER_ID', 'SEASON_ID', 'LEAGUE_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'PLAYER_AGE']
            
            # Add fields for each stat, using the display name from the mapping if available
            for stat_name, stat_value in latest_year_stats.items():
                if stat_name not in stats_to_skip:
                    # Check if there's a mapping for this stat
                    if stat_name in stat_name_mapping:
                        display_name, multiply_by_100 = stat_name_mapping[stat_name]
                        if multiply_by_100:
                            # Multiply the value by 100 and add a '%' at the end
                            stat_value = f"{stat_value * 100:.1f}%"
                    else:
                        display_name = stat_name  # Use the original name
                    padded_value = f"`{stat_value}`"
                    embed.add_field(name=display_name, value=padded_value, inline=True)

            # Respond to the interaction
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except:
            await interaction.response.send_message(f"Player {player_name} not found.", ephemeral=True)

    @tree.command(name='player_log', description='Show the player\'s performance of their last 10 games.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def player_stats(interaction, player_name: str):
        try:
            # Use the nba_api to search for a player
            player = players.find_players_by_full_name(player_name)
            player_id = player[0]['id']
            player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            player_data = player_info.get_data_frames()[0].iloc[0]

            # Get the player's game log
            game_log = playergamelog.PlayerGameLog(player_id=player_id)
            player_stats = game_log.get_data_frames()[0]

            # Limit the number of rows to display
            max_rows = 10  # Adjust as needed
            player_stats = player_stats.head(max_rows)

            # Create a formatted message with limited information
            formatted_message = ""
            for index, row in player_stats.iterrows():
                game_info = row['GAME_DATE']
                matchup = row['MATCHUP']
                points = row['PTS']
                assists = row['AST']
                rebounds = row['REB']
                formatted_message += f"__{game_info} - {matchup}:__\nPoints: `{points}`, Assists: `{assists}`, Rebounds: `{rebounds}`\n\n"

            if formatted_message == "":
                formatted_message = "No games found. NBA possibly updating data."

            # Create the embed
            embed = discord.Embed(title=f"{player_data['DISPLAY_FIRST_LAST']}'s Last 10 Games:", description=formatted_message, color=0x339cff)
            embed.set_thumbnail(url=f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png")
            embed.set_footer(text="Data provided by NBA.com", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")

            # Respond to the interaction
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except:
            await interaction.response.send_message(f"Player {player_name} not found.", ephemeral=True)

    @tree.command(name='player_info', description='Show the player\'s more general information.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def player_stats(interaction, player_name: str):
        try:
            # Use the nba_api to search for a player
            player = players.find_players_by_full_name(player_name)
            player_id = player[0]['id']
            player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        
            player_data = player_info.get_data_frames()[0].iloc[0]

            # Create the embed
            embed = discord.Embed(title=f"{player_data['DISPLAY_FIRST_LAST']}:", color=0x339cff)
            embed.set_thumbnail(url=f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_data['PERSON_ID']}.png")
            embed.set_footer(text="Data provided by NBA.com", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")

            # Convert the birthdate to a datetime object
            birthdate_str = player_data['BIRTHDATE']
            birthdate = datetime.strptime(birthdate_str, '%Y-%m-%dT%H:%M:%S')

            # Calculate the age
            current_date = datetime.now()
            age = current_date.year - birthdate.year - ((current_date.month, current_date.day) < (birthdate.month, birthdate.day))

            # Add player info fields
            embed.add_field(name="Team", value=f"`{player_data['TEAM_ABBREVIATION'].upper()}`", inline=True)
            embed.add_field(name="Jersey Number", value=f"`#{player_data['JERSEY']}`", inline=True)
            embed.add_field(name="Position", value=f"`{player_data['POSITION']}`", inline=True)
            embed.add_field(name="Height", value=f"`{player_data['HEIGHT']}`", inline=True)
            embed.add_field(name="Weight", value=f"`{player_data['WEIGHT']} lbs`", inline=True)
            embed.add_field(name="Date of Birth", value=f"`{age} years old`", inline=True)
            embed.add_field(name="Drafted", value=f"`#{player_data['DRAFT_NUMBER']} - ({player_data['DRAFT_YEAR']})`", inline=True)
            embed.add_field(name="Last Affiliation", value=f"`{player_data['SCHOOL']}`", inline=True)
            embed.add_field(name="NBA Career", value=f"`{player_data['FROM_YEAR']} - {player_data['TO_YEAR']}`", inline=True)
            embed.add_field(name="Part of NBA75", value="`Yes`" if player_data['GREATEST_75_FLAG'] == 'Y' else "`No`", inline=True)
            embed.add_field(name="Player ID", value=f"`{player_data['PERSON_ID']}`", inline=True)
            embed.add_field(name="Status", value=f"`{player_data['ROSTERSTATUS']}`", inline=True)
            
            # Respond to the interaction
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except:
            await interaction.response.send_message(f"Player {player_name} not found.", ephemeral=True)

    @tree.command(name='league_leaders', description='Get a list of the top 20 players.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def league_leaders(interaction):
        # Use the NBA API to fetch league leaders data
        leaders = LeagueLeaders().get_data_frames()[0]

        # Limit the number of leaders to display (adjust as needed)
        max_leaders = 20
        leaders = leaders.head(max_leaders)
        print(leaders)

        # Create an embed to display the league leaders
        embed = discord.Embed(title='NBA League Leaders', color=0x339cff)

        # Iterate through the league leaders data and add fields to the message
        formatted_message = ""
        for index, row in leaders.iterrows():
            player_rank = row['RANK']
            player_name = row['PLAYER']
            minutes_played = row['MIN']
            points = row['PTS']
            formatted_message += f"**__({player_rank}) {player_name}:__** Points: {points}, Minutes Played: {minutes_played}\n"

        if formatted_message == "":
            formatted_message = "No league leaders found. NBA possibly updating data."

        # Create an embed to display the league leaders
        embed = discord.Embed(title='NBA League Leaders', description=formatted_message, color=0x339cff)

        # Set the footer and author information
        embed.set_footer(text="Data provided by NBA.com", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")

        # Send the message
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @tree.command(name='meme', description='Display a random top 50 hot post from r/Nbamemes.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def meme(interaction):
        try:
            reddit = asyncpraw.Reddit(client_id=settings["REDDIT_BOT_ID"],
                        client_secret=settings["REDDIT_BOT_SECRET"],
                        user_agent='BenSimmonsBot by Minisungam')
        except:
            await interaction.response.send_message("The Reddit meme grabber has not been setup.", ephemeral=True)
            return
        
        subreddit = await reddit.subreddit('Nbamemes')

        memes_submissions = []
        async for submission in subreddit.hot(limit=50):
            memes_submissions.append(submission)

        invalid = True
        while invalid:
            submission = random.choice(memes_submissions)
            # Imgur links not reliable (need to research into pulling reddit preview links)
            if submission.url.endswith(('.jpg', '.png', '.gif')) and "imgur" not in submission.url:
                    invalid = False
            elif len(memes_submissions) == 0:
                await interaction.response.send_message("There are no valid memes available.", ephemeral=True)
                return
            else:
                memes_submissions.remove(submission)
            
        author = await reddit.redditor(submission.author, fetch=True)

        embed = discord.Embed(title=submission.title, url=f"https://reddit.com{submission.permalink}", timestamp=datetime.fromtimestamp(submission.created_utc), color=0x9aff73)
        embed.set_image(url=str(submission.url))
        embed.set_footer(text=f"Posted by u/{author.name}", icon_url=author.icon_img)

        print(f"[{current_time()}] Meme: {interaction.user.name} requested a meme, sent {submission.url}")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        await reddit.close()

    ############# Bot Services #############
    async def start_update_scores():
        if settings["DAILY_SCORE_ENABLED"] is False:
            if settings["DAILY_SCORE_RUNNING"] is False:
                settings["DAILY_SCORE_ENABLED"] = True
                dotenv.set_key(dotenv_file, "DAILY_SCORE_ENABLED", "True")
                client.loop.create_task(fetch_and_display_games(client))
                return("Daily scores service started")
            else:
                return("Daily scores service was recently shut down, please try again in a few minutes")
        else:
            return("Daily scores service already running")
            
    async def stop_update_scores():
        if settings["DAILY_SCORE_ENABLED"] is True:
            settings["DAILY_SCORE_ENABLED"] = False
            dotenv.set_key(dotenv_file, "DAILY_SCORE_ENABLED", "False")
            return("Daily scores service stopped")
        else:
            return("Daily scores service already stopped")

    async def start_update_trades():
        if settings["TRANSACTIONS_ENABLED"] is False:
            if settings["TRANSACTIONS_RUNNING"] is False:
                settings["TRANSACTIONS_ENABLED"] = True
                dotenv.set_key(dotenv_file, "TRANSACTIONS_ENABLED", "True")
                client.loop.create_task(fetch_and_display_trades(client))
                return("Transactions service started")
            else:
                return("Transactions service was recently shut down, please try again in a few minutes")
        else:
            return("Transactions service already running")

    async def stop_update_trades():
        if settings["TRANSACTIONS_ENABLED"] is True:
            settings["TRANSACTIONS_ENABLED"] = False
            dotenv.set_key(dotenv_file, "TRANSACTIONS_ENABLED", "False")
            return("Transactions service stopped")
        else:
            return("Transactions service already stopped")
        
    client.run(settings["BOT_TOKEN"])