import discord, bot , asyncio, db, os, functools, typing
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException
from bs4 import BeautifulSoup
from datetime import date
from nba_api.stats.endpoints import scoreboardv2
import requests

nba_transactions_url = "https://www.nba.com/players/transactions"

def current_time():
    current_time = datetime.now()
    formatted_time: str = current_time.strftime("%H:%M:%S")
    return formatted_time

def run_fetch_trades(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper():
        return await asyncio.to_thread(func)
    return wrapper

@run_fetch_trades
def fetch_trades():
    # Configure the Chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # Create the driver
    driver = webdriver.Chrome(options=options)
    try:
        print(f"[{current_time()}] Trades: Created driver")

        # Fetch the page source
        driver.get(nba_transactions_url)
        driver.implicitly_wait(30)

        return driver.page_source
    except (WebDriverException, TimeoutException) as e:
        print(f"[{current_time()}] Trades: An error occurred while fetching trades: {str(e)}")
    finally:
        # Close the driver
        driver.quit()
        print(f"[{current_time()}] Trades: Closed the driver")

async def fetch_and_display_trades_new(client):
    # New function to get transactions using https://stats.nba.com/js/data/playermovement/NBA_Player_Movement.json
    # No more selenium!
    bot.settings["TRANSACTIONS_RUNNING"] = True

async def fetch_and_display_trades(client):
    bot.settings["TRANSACTIONS_RUNNING"] = True
    try:
        debug_channel = client.get_channel(bot.settings["DEBUG_CHANNEL_ID"])

        while os.environ['TRANSACTIONS_ENABLED'] == "True":       

            page_source = await fetch_trades()
            print(f"[{current_time()}] Trades: Fetched page source")

            # Parse the HTML content
            soup = BeautifulSoup(page_source, "html.parser")
            print(f"[{current_time()}] Trades: Parsed page source")

            # Extract player trade information
            trades = soup.find_all("div", class_="TransactionSingle_base__y2kG1")
            trades.reverse()

            if trades:
                if len(trades) == 0:
                    print(f"[{current_time()}] Trades: No trades found")
                else:
                    print(f"[{current_time()}] Trades: Found {len(trades)} trades")

                posted_trades_tuples = db.get_all_transactions()
                posted_trades = [item[0] for item in posted_trades_tuples]
                skipped = 0
                added = 0

                # Format and post new trades to Discord
                for trade in trades:
                    trade_details = trade.find("div", class_="TransactionSingle_desc__uG447").text.strip()
                    player_image = trade.find("img", class_="PlayerImage_image__wH_YX")
                    player_image_url = player_image['src']
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

            print(f"[{current_time()}] Trades: Sleeping for 10 minutes")
            await asyncio.sleep(600)

    except Exception as e:
        await debug_channel.send(f"Trades error: ```{str(e)}```")
        print(f"[{current_time()}] Trades: Error: {str(e)}")
    finally:
        await debug_channel.send("Trades service has stopped.")
        bot.settings["TRANSACTIONS_ENABLED"] = False
        bot.settings["TRANSACTIONS_RUNNING"] = False
        print(f"[{current_time()}] Trades: fully exited.")


async def fetch_and_display_games(client):
    global last_sent_message
    bot.settings["DAILY_SCORE_RUNNING"] = True
    if settings['DAILY_SCORE_MESSAGE_ID'] != 0:
        try:
            debug_channel = client.get_channel(bot.settings["DEBUG_CHANNEL_ID"])

            while os.environ['DAILY_SCORE_ENABLED'] == "True":
                todaysScoreboard = requests.get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json").json()
                scoreboard_info = todaysScoreboard["scoreboard"]
                games = scoreboard_info["games"]

                # Get the current date from the scoreboard data
                scoreboard_date = datetime.datetime.strptime(scoreboard_info["gameDate"], "%Y-%m-%d").date()

                # Check if the date has changed
                if has_date_changed(scoreboard_date):
                    embed = discord.Embed(title="Today's Scores", color=0xf52f63)
                else:
                    embed = discord.Embed(title="Updated Scores", color=0xf52f63)

                for game in games:
                    game_info = {
                        "Game ID": game["gameId"],
                        "Game Status": game["gameStatusText"],
                        "Time": f"Q{game['period']} {game['gameClock']}",
                        "Home Team City": game["homeTeam"]["teamCity"],
                        "Home Team Name": game["homeTeam"]["teamName"],
                        "Away Team City": game["awayTeam"]["teamCity"],
                        "Away Team Name": game["awayTeam"]["teamName"],
                        "Home Team Score": game["homeTeam"]["score"],
                        "Away Team Score": game["awayTeam"]["score"],
                    }

                    embed.add_field(
                        name=f"**Home: {game_info['Home Team City']} {game_info['Home Team Name']} VS Away: {game_info['Away Team City']} {game_info['Away Team Name']}**\n", 
                        value=f"Time: {game_info['Time']}\nScore: {game_info['Home Team Name']} {game_info['Home Team Score']} - {game_info['Away Team Name']} {game_info['Away Team Score']}", 
                        inline=False
                    )

                # Send a new message or edit the existing one
                if last_sent_message:
                    await last_sent_message.edit(embed=embed)
                else:
                    last_sent_message = await debug_channel.send(embed=embed)

                await asyncio.sleep(300)  # Update every 5 minutes

        except Exception as e:
            await debug_channel.send(f"Daily score error: ```{str(e)}```")
            print(f"[{current_time()}] Daily Score: Error intended, will be fixed once season starts.")
        finally:  
            await debug_channel.send("Daily score service has stopped.")
            bot.settings["DAILY_SCORE_ENABLED"] = False
            bot.settings["DAILY_SCORE_RUNNING"] = False
            print(f"[{current_time()}] Daily Score: Fully exited.")