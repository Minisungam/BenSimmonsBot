import discord, bot, asyncio, db, os, json
from datetime import datetime
import aiohttp
import sqlite3

nba_transactions_url = "https://www.nba.com/players/transactions"

def current_time():
    current_time = datetime.now()
    formatted_time: str = current_time.strftime("%H:%M:%S")
    return formatted_time

def get_wait_time(retry_count):
    wait_times = [5, 10, 15, 30, 60, 120, 180, 300, 600, 900, 1800, 3600]
    
    # Use the last wait time for all subsequent retries if retry_count exceeds the list length
    return wait_times[min(retry_count, len(wait_times) - 1)]

async def fetch_image_url(player_id):
    base_url = "https://cdn.nba.com/headshots/nba/latest/260x190/"
    player_image_url = f"{base_url}{int(player_id)}.png"

    async with aiohttp.ClientSession() as session:
        async with session.head(player_image_url) as response:
            if response.status == 200:
                return player_image_url
            else:
                return f"{base_url}fallback.png"   

async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.text()
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    raise ValueError(f"Failed to decode data from {url}. It does not contain valid JSON data.")
            else:
                raise ValueError(f"Failed to fetch data from {url}. Status code: {response.status}")

async def fetch_and_display_trades(client):
    # Prevent multiple instances of the service from running
    if (bot.settings["TRANSACTIONS_RUNNING"] == True):
        return;

    # Check if debug channel is set
    debug_channel = None
    try:
        debug_channel = client.get_channel(bot.settings["DEBUG_CHANNEL_ID"])
    except:
        bot.settings["DEBUG_OUTPUT"] = False
        print(f"[{current_time()}] Bot: Debug channel not found. Disabling debug output.")

    # Check if transaction channel is set
    try:
        transaction_channel = client.get_channel(bot.settings["TRANSACTION_CHANNEL_ID"])
    except:
        print(f"[{current_time()}] Trades: Trades channel not found. Disabling trades.")
        bot.settings["TRANSACTIONS_ENABLED"] = False
        bot.settings["TRANSACTIONS_RUNNING"] = False
        print(f"[{current_time()}] Trades: fully exited.")
        return

    bot.settings["TRANSACTIONS_RUNNING"] = True
    try:
        while os.environ['TRANSACTIONS_ENABLED'] == "True":
            retry_count = 0
            while retry_count < 13:
                try:
                    request = await fetch_json("https://stats.nba.com/js/data/playermovement/NBA_Player_Movement.json")
                    break
                except Exception as e:
                    print(f"[{current_time()}] Trades: Error fetching data. Retry #{retry_count}...")
                    print(f"[{current_time()}] {str(e)}")
                    await asyncio.sleep(get_wait_time(retry_count))
                    retry_count += 1

            if retry_count >= 13:
                print(f"[{current_time()}] Trades: Error fetching data.")
                return
                
            trades = request["NBA_Player_Movement"]["rows"][:50]
            trades.reverse()

            posted_trades_tuples = db.get_all_transactions()
            posted_trades = [item[0] for item in posted_trades_tuples]
            added = 0

            # Format and post new trades to Discord
            for trade in trades:
                trade_details = trade["TRANSACTION_DESCRIPTION"]
                
                # Check if the trade has been posted before
                if trade_details not in posted_trades:
                    # Post the trade to Discord
                    player_image_url = await fetch_image_url(trade['PLAYER_ID'])  

                    formatted_trade = discord.Embed(title="New Player Transaction", description=trade_details, color=0xf52f63, timestamp=datetime.now(), url=nba_transactions_url)
                    formatted_trade.set_thumbnail(url=player_image_url)
                    formatted_trade.set_footer(text=f"NBA", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")
                    
                    await transaction_channel.send(embed=formatted_trade)
                    await asyncio.sleep(1)

                    # Add the trade to the list of posted trades
                    try:
                        db.add_transaction(trade_details)
                        posted_trades.append(trade_details)
                        added += 1
                    except sqlite3.IntegrityError as e:
                        print(f"[{current_time()}] Trades: Error adding trade to database.")
                        print(f"[{current_time()}] {str(e)}")
                        if bot.settings["DEBUG_OUTPUT"]:
                            await debug_channel.send(f"Trades error: ```{str(e)}```")

            if added > 0:
                print(f"[{current_time()}] Trades: Found new trades. Added " + str(added) + " trades.")

            db.commit()
            await asyncio.sleep(600)

    except Exception as e:
        if bot.settings["DEBUG_OUTPUT"]:
            await debug_channel.send(f"Trades error: ```{str(e)}```")
        print(f"[{current_time()}] Trades: Error: {str(e)}")
    finally:
        if bot.settings["DEBUG_OUTPUT"]:
            await debug_channel.send("Trades service has stopped.")
        bot.settings["TRANSACTIONS_ENABLED"] = False
        bot.settings["TRANSACTIONS_RUNNING"] = False
        print(f"[{current_time()}] Trades: fully exited.")

async def fetch_and_display_games(client):
    # Prevent multiple instances of the service from running
    if (bot.settings["DAILY_SCORE_RUNNING"] == True):
        return;

    debug_channel = None
    daily_score_channel = None

    # Check if debug channel is set
    try:
        debug_channel = client.get_channel(bot.settings["DEBUG_CHANNEL_ID"])
    except:
        bot.settings["DEBUG_OUTPUT"] = False
        print(f"[{current_time()}] Bot: Debug channel not found. Disabling debug output.")

    # Check if daily score channel is set
    try:
        daily_score_channel = client.get_channel(bot.settings["DAILY_SCORE_CHANNEL_ID"])
    except:
        print(f"[{current_time()}] Daily Score: Daily score channel not found. Disabling daily score.")
        bot.settings["TRANSACTIONS_ENABLED"] = False
        bot.settings["TRANSACTIONS_RUNNING"] = False
        print(f"[{current_time()}] Daily Score: fully exited.")
        return

    bot.settings["DAILY_SCORE_RUNNING"] = True
    try:
        while os.environ['DAILY_SCORE_ENABLED'] == "True":
            new_message = False
            
            retry_count = 0
            while retry_count < 13:
                try:
                    todaysScoreboard = await fetch_json("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json")
                    break
                except Exception as e:
                    print(f"[{current_time()}] Daily Score: Error fetching data. Retry #{retry_count}...")
                    print(f"[{current_time()}] Error: {str(e)}")
                    await asyncio.sleep(get_wait_time(retry_count))
                    retry_count += 1

            if retry_count >= 13:
                print(f"[{current_time()}] Daily Score: Error fetching data.")
                return
            
            scoreboard_info = todaysScoreboard["scoreboard"]
            games = scoreboard_info["games"]

            # Get the current date from the scoreboard data
            scoreboard_date = datetime.strptime(scoreboard_info["gameDate"], "%Y-%m-%d").date()
            suffix = "th" if 11 <= scoreboard_date.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(scoreboard_date.day % 10, 'th')
            day_formatted = str(scoreboard_date.day).lstrip('0') if scoreboard_date.day < 10 else str(scoreboard_date.day)
            embed_title = f"Scores for {str(scoreboard_date.strftime('%B ' + day_formatted + suffix + ', %Y'))}"
        
            # Get the last message sent in the channel
            latest_message = [message async for message in daily_score_channel.history(limit=1)]
            last_message_sent = latest_message[0]

            # Abort if the last message sent is not found for whatever reason
            if last_message_sent is None:
                raise Exception("Last message sent not found.")

            # Compare the title of the last message sent to the current title
            latest_message_embed = latest_message[0].embeds[0]
            if latest_message_embed.title != embed_title:
                new_message = True
                print(f"[{current_time()}] Daily Score: Date has changed. Creating new message.")

            # Create the embed
            embed = discord.Embed(title=embed_title, color=0xf52f63)

            # Add the games to the embed
            for game in games:
                game_info = {
                    "Game ID": game["gameId"],
                    "Game Status": game["gameStatusText"],
                    "Period": game['period'],
                    "Game Status": game['gameStatus'],
                    "Game Status Text": game['gameStatusText'].strip(),
                    "Game Clock": game['gameClock'].strip(),
                    "Home Team City": game["homeTeam"]["teamCity"].strip(),
                    "Home Team Name": game["homeTeam"]["teamName"].strip(),
                    "Away Team City": game["awayTeam"]["teamCity"].strip(),
                    "Away Team Name": game["awayTeam"]["teamName"].strip(),
                    "Home Team Score": game["homeTeam"]["score"],
                    "Away Team Score": game["awayTeam"]["score"],
                } 

                # Game Status: 1 = Pre-Game, 2 = In-Progress, 3 = Final
                if game_info["Game Status"] == 1:
                    embed.add_field(
                        name=f"**{game_info['Home Team City']} {game_info['Home Team Name']} VS {game_info['Away Team City']} {game_info['Away Team Name']}**\n",
                        value=f"Game starting at: {game_info['Game Status Text']}", 
                        inline=False
                    )
                elif game_info["Game Status"] == 2:
                    # Format the game clock
                    if game_info["Game Clock"] == "":
                        game_info["Game Clock"] = "PT00M00.00S"
                    elif ":" in game_info["Game Clock"]:
                        pass
                    else:
                        game_info["Game Clock"] = game_info["Game Clock"].replace("PT", "").replace("S", "")
                        parsed_time = datetime.strptime(game_info["Game Clock"], "%MM%S.%f")
                        game_info["Game Clock"] = str(datetime.strftime(parsed_time, "%M:%S"))

                    embed.add_field(
                    name=f"**{game_info['Home Team City']} {game_info['Home Team Name']} VS {game_info['Away Team City']} {game_info['Away Team Name']}**\n", 
                    value=f"Time: `Q{game_info['Period']} {game_info['Game Clock']}`\n{game_info['Home Team Name']}: `{game_info['Home Team Score']}`\n{game_info['Away Team Name']}: `{game_info['Away Team Score']}`", 
                    inline=False
                    )
                elif game_info["Game Status"] == 3:
                    embed.add_field(
                    name=f"**{game_info['Home Team City']} {game_info['Home Team Name']} VS {game_info['Away Team City']} {game_info['Away Team Name']}**\n", 
                    value=f"**Final Score**\n{game_info['Home Team Name']}: `{game_info['Home Team Score']}`\n{game_info['Away Team Name']}: `{game_info['Away Team Score']}`", 
                    inline=False
                    )
                else:
                    pass
                    
            # Add a message if there are no games today
            if len(games) == 0:
                embed.add_field(
                    name="No games today.",
                    value="Check back tomorrow!",
                    inline=False
                )        
            
            # Send new message or edit the last message
            if new_message:
                # Send the message to Discord
                await daily_score_channel.send(embed=embed)
            else:
                # Edit the last message
                await last_message_sent.edit(embed=embed)


            await asyncio.sleep(60)  # Update every minute

    except Exception as e:
        if bot.settings["DEBUG_OUTPUT"]:
            await debug_channel.send(f"Daily score error: ```{str(e)}```")
        print(f"[{current_time()}] Daily Score: {str(e)}")
    finally:
        if bot.settings["DEBUG_OUTPUT"]:  
            await debug_channel.send("Daily score service has stopped.")
        bot.settings["DAILY_SCORE_ENABLED"] = False
        bot.settings["DAILY_SCORE_RUNNING"] = False
        print(f"[{current_time()}] Daily Score: Fully exited.")