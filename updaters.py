import discord, bot , asyncio, db, os, functools, typing
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException
from bs4 import BeautifulSoup
from datetime import date
from nba_api.stats.endpoints import scoreboardv2

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
                    formatted_trade = discord.Embed(title="**__New Player Transaction__**", description=trade_details, color=0xf52f63, timestamp=datetime.now(), url=nba_transactions_url)
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
    bot.settings["DAILY_SCORE_RUNNING"] = True
    try:
        debug_channel = client.get_channel(bot.settings["DEBUG_CHANNEL_ID"])

        while os.environ['DAILY_SCORE_ENABLED'] == "True":
            # Fetch the list of games for the current day using NBA API
            today = date.today().strftime('%Y-%m-%d')
            print(f"[{current_time()}] Daily Score: Fetching games for {today}")
            response = scoreboardv2.ScoreboardV2(game_date=today)

            print(response)

            game_message = db.get_current_day_games()[1]

            games = response.get_data_frames()[0]
            print(games)
            
            try:
                # Create a formatted message with game information
                formatted_message = "Current Day's NBA Games:\n"
                for index, game in games.iterrows():
                    formatted_message += f"{game['GAMECODE']} - {game['GAME_STATUS_TEXT']} ({game['GAME_CLOCK']})\n"

                # Update the message with the list of games
                if bot.game_message != "":
                    await bot.game_message.edit(content=formatted_message)
                else:
                    # If the message doesn't exist yet, send a new message
                    bot.game_message = await client.get_channel(bot.settings["TODAYS_GAMES_CHANNEL_ID"]).send(formatted_message)
            except IndexError:
                return
            except Exception as e:
                # Handle any exceptions that might occur while processing the data
                print(f"[{current_time()}] Daily Score: Error processing NBA data: {e}")
        else:
            # Handle the case when there are no games for the current day
            formatted_message = "No NBA games scheduled for today."

            if bot.game_message is not None:
                await bot.game_message.edit(content=formatted_message)
            else:
                game_message = await client.get_channel(bot.settings["TODAYS_GAMES_CHANNEL_ID"]).send(formatted_message)

            await asyncio.sleep(300)  # Update every 5 minutes

    except Exception as e:
        await debug_channel.send(f"Daily score error: ```{str(e)}```")
        print(f"[{current_time()}] Daily Score: Error intended, will be fixed once season starts.")
    finally:  
        await debug_channel.send("Daily score service has stopped.")
        bot.settings["DAILY_SCORE_ENABLED"] = False
        bot.settings["DAILY_SCORE_RUNNING"] = False
        print(f"[{current_time()}] Daily Score: Fully exited.")