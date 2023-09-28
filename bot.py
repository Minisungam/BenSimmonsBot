import os
import responses
import updaters
import db
import discord
import asyncio
import concurrent.futures
from datetime import datetime
from discord import app_commands
import dotenv
import nba_api.stats.static.players as players
from nba_api.stats.endpoints import playercareerstats, playergamelog, commonplayerinfo, LeagueLeaders

settings = {
    "TOKEN": "",
    "GUILD_ID": 0,
    "BOT_OWNER_ID": 0,
    "TRANSACTION_CHANNEL_ID": 0,
    "TODAYS_GAMES_CHANNEL_ID": 0,
    "DAILY_SCORE_ENABLED": False,
    "TRANSACTIONS_ENABLED": False
}

async def send_message(message, user_message, is_private):
    try:
        response = responses.get_response(user_message)
        if response is not None:
            await message.author.send(response) if is_private else await message.channel.send(response)
        else:
            return
    except Exception as e:
        print(e)
        await message.channel.send("An error occurred. Please try again.")

def run_discord_bot():
    # Load environment variables
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)
    try:
        if os.getenv('BOT_TOKEN') == "":
            raise Exception
        else:
            settings["TOKEN"]: str = os.getenv('BOT_TOKEN')
        settings["GUILD_ID"]: int = int(os.getenv('GUILD_ID'))
        settings["BOT_OWNER_ID"]: int = int(os.getenv('BOT_OWNER_ID'))
        settings["TRANSACTION_CHANNEL_ID"]: int = int(os.getenv('TRANSACTION_CHANNEL_ID'))
        settings["TODAYS_GAMES_CHANNEL_ID"]: int = int(os.getenv('TODAYS_GAMES_CHANNEL_ID'))
    except:
        print("Bot: Environment variables missing in .env file.")
        return
    try:
        settings["DAILY_SCORE_ENABLED"] : bool = eval(os.getenv('DAILY_SCORE_ENABLED'))
    except:
        settings["DAILY_SCORE_ENABLED"] : bool = False
        print("Bot: DAILY_SCORE_ENABLED setting incorrect in .env file, must be \"True\" or \"False\". Defaulting to False.")
    try:
        settings["TRANSACTIONS_ENABLED"]: bool = eval(os.getenv('TRANSACTIONS_ENABLED'))
    except:
        settings["TRANSACTIONS_ENABLED"]: bool = False
        print("Bot: TRANSACTIONS_ENABLED setting incorrect in .env file, must be \"True\" or \"False\". Defaulting to False.")


    # Bot setup
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    ############# Bot events #############
    @client.event
    async def on_ready():
        print(f'{client.user} has connected to Discord!')
        if settings["DAILY_SCORE_ENABLED"] :
            settings["DAILY_SCORE_ENABLED"]  = False
            await start_update_scores()
            print("Bot: Daily scores service started")
        else:
            print("Bot: Daily scores service disabled")
        if settings["TRANSACTIONS_ENABLED"]:
            settings["TRANSACTIONS_ENABLED"] = False
            await start_update_trades()
            print("Bot: Transactions service started")
        else:
            print("Bot: Transactions service disabled")
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="badly, no 3s."))
        print("Bot: Presence set")
        await tree.sync(guild=discord.Object(id=settings["GUILD_ID"]))
        print("Bot: Commands synced")

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

    ############# Bot commands #############
    @tree.command(name='daily_scores', description='Enables or disables the daily scores service.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def daily_scores(interaction, enable: bool):
        if interaction.user.id == settings["BOT_OWNER_ID"]:
            if enable is True:
                response = start_update_scores()
                await interaction.response.send_message(response, ephemeral=True)
            else:
                response = stop_update_scores()
                await interaction.response.send_message(response, ephemeral=True)
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    @tree.command(name='transactions', description='Enables or disables the transactions service.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def transactions(interaction, enable: bool):
        if interaction.user.id == settings["BOT_OWNER_ID"]:
            if enable is True:
                response = start_update_trades()
                await interaction.response.send_message(response, ephemeral=True)
            else:
                response = stop_update_trades()
                await interaction.response.send_message(response, ephemeral=True)
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    @tree.command(name='shutdown', description='Shuts down the bot', guild=discord.Object(id=settings["GUILD_ID"]))
    async def quit_bot(interaction):
        if interaction.user.id == settings["BOT_OWNER_ID"]:
            db.commit()
            db.close()
            await interaction.response.send_message("Shutting down in 5 seconds", ephemeral=True)
            print("Bot: Shutting down")
            await asyncio.sleep(5)
            await client.close()
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    @tree.command(name='player_stats', description='Gets the player\'s stats for the season.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def player_stats(interaction, player_name: str):
        # Use the nba_api to search for a player
        player_info = players.find_players_by_full_name(player_name)
        if player_info:
            player_id = player_info[0]['id']
            # Get the player's game log
            career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
            career_stats_df = career_stats.get_data_frames()[0]

            # Get the latest year of data
            latest_year_stats = career_stats_df.iloc[-1]

            # Create the embed
            embed = discord.Embed(title=f"Player Stats for {player_name}:", description=f"Team: `{latest_year_stats['TEAM_ABBREVIATION']}`", color=0x339cff)
            embed.set_thumbnail(url=f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png")
            embed.set_footer(text="Data provided by NBA.com", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")

            stat_name_mapping = {
                'FG_PCT': ('FG%', True),
                'FG3_PCT': ('FG3%', True),
                'FT_PCT': ('FT%', True)
            }

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
        else:
            await interaction.response.send_message(f"Player {player_name} not found.", ephemeral=True)

    @tree.command(name='player_log', description='Show the player\'s performance of their last 10 games.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def player_stats(interaction, player_name: str):
        # Use the nba_api to search for a player
        player_info = players.find_players_by_full_name(player_name)
        if player_info:
            player_id = player_info[0]['id']
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

            # Create the embed
            embed = discord.Embed(title=f"{player_name}'s Last 10 Games:", description=formatted_message, color=0x339cff)
            embed.set_thumbnail(url=f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png")
            embed.set_footer(text="Data provided by NBA.com", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")

            # Respond to the interaction
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await interaction.response.send_message(f"Player {player_name} not found.", ephemeral=True)

    @tree.command(name='player_info', description='Show the player\'s more general information.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def player_stats(interaction, player_name: str):
        # Use the nba_api to search for a player
        player_id = players.find_players_by_full_name(player_name)
        player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id[0]['id'])
        
        if player_info:
            player_data = player_info.get_data_frames()[0].iloc[0]

            # Create the embed
            embed = discord.Embed(title=f"{player_name}:", color=0x339cff)
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
        else:
            await interaction.response.send_message(f"Player {player_name} not found.", ephemeral=True)

    @tree.command(name='league_leaders', description='Get a list of the top 15 players.', guild=discord.Object(id=settings["GUILD_ID"]))
    async def league_leaders(interaction):
        # Use the NBA API to fetch league leaders data
        leaders = LeagueLeaders().get_data_frames()[0]

        # Limit the number of leaders to display (adjust as needed)
        max_leaders = 20
        leaders = leaders.head(max_leaders)

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

        # Create an embed to display the league leaders
        embed = discord.Embed(title='NBA League Leaders', description=formatted_message, color=0x339cff)

        # Set the footer and author information
        embed.set_footer(text="Data provided by NBA.com", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")

        # Send the message
        await interaction.response.send_message(embed=embed, ephemeral=False)

    ############# Bot services #############
    async def start_update_scores():
        if settings["DAILY_SCORE_ENABLED"]  is False:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(updaters.fetch_and_display_games(client, settings["TODAYS_GAMES_CHANNEL_ID"]))
            print("Bot: Daily scores service started")
            return("Daily scores service started")
        else:
            print("Bot: Daily scores service already running")
            return("Daily scores service already running")
            
    async def stop_update_scores():
        if settings["DAILY_SCORE_ENABLED"]  is True:
            settings["DAILY_SCORE_ENABLED"]  = False
            os.environ["DAILY_SCORE_ENABLED"] = "False"
            dotenv.set_key(dotenv_file, "DAILY_SCORE_ENABLED", "False")
            print("Bot: Daily scores service stopped")
            return("Daily scores service stopped")
        else:
            print("Bot: Daily scores service already stopped")
            return("Daily scores service already stopped")

    async def start_update_trades():
        if settings["TRANSACTIONS_ENABLED"] is False:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(updaters.fetch_and_display_trades(client, settings["TRANSACTION_CHANNEL_ID"]))
            print("Bot: Transactions service started")
            return("Transactions service started")
        else:
            print("Bot: Transactions service already running")
            return("Transactions service already running")

    async def stop_update_trades():
        if settings["TRANSACTIONS_ENABLED"] is True:
            settings["TRANSACTIONS_ENABLED"] = False
            os.environ["TRANSACTIONS_ENABLED"] = "False"
            dotenv.set_key(dotenv_file, "TRANSACTIONS_ENABLED", "False")
            print("Bot: Transactions service stopped")
            return("Transactions service stopped")
        else:
            print("Bot: Transactions service already stopped")
            return("Transactions service already stopped")

    client.run(settings["TOKEN"])
