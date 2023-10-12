import discord, bot, asyncio, db, os, requests
from datetime import datetime

nba_transactions_url = "https://www.nba.com/players/transactions"

def current_time():
    current_time = datetime.now()
    formatted_time: str = current_time.strftime("%H:%M:%S")
    return formatted_time

async def fetch_and_display_trades(client):
    # Check if debug channel is set
    debug_channel = None
    try:
        debug_channel = client.get_channel(bot.settings["DEBUG_CHANNEL_ID"])
    except:
        bot.settings["DEBUG_OUTPUT"] = False
        print(f"[{current_time()}] Bot: Debug channel not found. Disabling debug output.")

    bot.settings["TRANSACTIONS_RUNNING"] = True
    try:
        while os.environ['TRANSACTIONS_ENABLED'] == "True":
            request = requests.get("https://stats.nba.com/js/data/playermovement/NBA_Player_Movement.json").json()
            trades = request["NBA_Player_Movement"]["rows"][:50]
            trades.reverse()

            posted_trades_tuples = db.get_all_transactions()
            posted_trades = [item[0] for item in posted_trades_tuples]
            skipped = 0
            added = 0

            # Format and post new trades to Discord
            for trade in trades:
                trade_details = trade["TRANSACTION_DESCRIPTION"]
                trade_image_url = f"https://cdn.nba.com/headshots/nba/latest/260x190/{int(trade['PLAYER_ID'])}.png"
                
                # Check player image is available
                response = requests.get(trade_image_url)
                content_type = response.headers['content-type'].lower()
                if content_type == 'image/png':
                    player_image_url = trade_image_url
                else:
                    player_image_url = "https://cdn.nba.com/headshots/nba/latest/260x190/fallback.png"

                formatted_trade = discord.Embed(title="New Player Transaction", description=trade_details, color=0xf52f63, timestamp=datetime.now(), url=nba_transactions_url)
                formatted_trade.set_thumbnail(url=player_image_url)
                formatted_trade.set_footer(text=f"NBA", icon_url="https://pbs.twimg.com/profile_images/1692188312759341056/Eb9QQok7_200x200.jpg")

                # Check if the trade has been posted before
                if trade_details not in posted_trades:
                    # Post the trade to Discord
                    transaction_channel = client.get_channel(bot.settings["TRANSACTION_CHANNEL_ID"])
                    await transaction_channel.send(embed=formatted_trade)
                    await asyncio.sleep(1)

                    # Add the trade to the list of posted trades
                    added += 1
                    db.add_transaction(trade_details)
                else:
                    skipped += 1

            print(f"[{current_time()}] Trades: Skipped " + str(skipped) + ". Added " + str(added) + ".")
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
    # Check if debug channel is set
    debug_channel = None
    try:
        debug_channel = client.get_channel(bot.settings["DEBUG_CHANNEL_ID"])
    except:
        bot.settings["DEBUG_OUTPUT"] = False
        print(f"[{current_time()}] Bot: Debug channel not found. Disabling debug output.")

    bot.settings["DAILY_SCORE_RUNNING"] = True
    try:
        daily_score_channel = client.get_channel(bot.settings["DAILY_SCORE_CHANNEL_ID"])

        while os.environ['DAILY_SCORE_ENABLED'] == "True":
            new_message = False
            # Fetch the last sent message using the message ID
            try:
                last_message_sent = await daily_score_channel.fetch_message(bot.settings['DAILY_SCORE_LAST_MESSAGE_ID'])
            except:
                last_message_sent = None
                new_message = True
                print(f"[{current_time()}] Daily Score: Message not found. Creating new message.")

            todaysScoreboard = requests.get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json").json()
            scoreboard_info = todaysScoreboard["scoreboard"]
            games = scoreboard_info["games"]

            # Get the current date from the scoreboard data
            scoreboard_date = datetime.strptime(scoreboard_info["gameDate"], "%Y-%m-%d").date()
            
            # Check if the date has changed
            if str(scoreboard_date) != str(datetime.now().strftime("%Y-%m-%d")):
                new_message = True
                print(f"[{current_time()}] Daily Score: Date has changed. Creating new message.")

            embed = discord.Embed(title=f"Scores for {str(scoreboard_date.strftime('%B %dth, %Y'))}", color=0xf52f63)

            for game in games:
                game_info = {
                    "Game ID": game["gameId"],
                    "Game Status": game["gameStatusText"],
                    "Period": f"{game['period']}",
                    "Game Status Text": f"{game['gameStatusText']}",
                    "Time": f"Q{game['period']} {game['gameClock']}",
                    "Home Team City": game["homeTeam"]["teamCity"],
                    "Home Team Name": game["homeTeam"]["teamName"],
                    "Away Team City": game["awayTeam"]["teamCity"],
                    "Away Team Name": game["awayTeam"]["teamName"],
                    "Home Team Score": game["homeTeam"]["score"],
                    "Away Team Score": game["awayTeam"]["score"],
                }

                if game_info["Period"] == "0":
                    embed.add_field(
                        name=f"**{game_info['Home Team City']} {game_info['Home Team Name']} VS {game_info['Away Team City']} {game_info['Away Team Name']}**\n",
                        value=f"Game starting at: {game_info['Game Status Text']}", 
                        inline=False
                    )
                else:
                    embed.add_field(
                    name=f"**{game_info['Home Team City']} {game_info['Home Team Name']} VS {game_info['Away Team City']} {game_info['Away Team Name']}**\n", 
                    value=f"Time: `{game_info['Time']}`\n{game_info['Home Team Name']}: `{game_info['Home Team Score']}`\n{game_info['Away Team Name']}: `{game_info['Away Team Score']}`", 
                    inline=False
                    )

            if new_message:
                # Send the message to Discord
                await daily_score_channel.send(embed=embed)
                bot.settings['DAILY_SCORE_LAST_MESSAGE_ID'] = daily_score_channel.last_message_id
                bot.settings['DAILY_SCORE_LAST_DATE'] = datetime.now().strftime("%Y-%m-%d")
                bot.update_env_file()
            else:
                # Edit the message
                await last_message_sent.edit(embed=embed)

            await asyncio.sleep(15)  # Update every 15 seconds

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