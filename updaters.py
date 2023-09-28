import discord
from datetime import datetime
import bot
import asyncio
import db
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import date
from nba_api.stats.endpoints import scoreboardv2



async def fetch_and_display_trades(client, CHANNEL_ID):
    try:
        while os.environ['TRANSACTIONS_ENABLED'] == "True":
            nba_transactions_url = "https://www.nba.com/players/transactions"
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            driver = webdriver.Chrome(options=options)
            print("Trades: Created driver")

            driver.get(nba_transactions_url)
            driver.implicitly_wait(30)

            page_source = driver.page_source
            print("Trades: Fetched page source")

            driver.close()
            print("Trades: Closed the driver")

            # Parse the HTML content
            soup = BeautifulSoup(page_source, "html.parser")
            print("Trades: Parsed page source")

            # Extract player trade information
            trades = soup.find_all("div", class_="TransactionSingle_base__y2kG1")
            trades.reverse()

            if len(trades) == 0:
                print("Trades: No trades found")
            else:
                print(f"Trades: Found {len(trades)} trades")

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
                    channel = client.get_channel(CHANNEL_ID)
                    await channel.send(embed=formatted_trade)
                    await asyncio.sleep(1)

                    # Add the trade to the list of posted trades
                    added += 1
                    db.add_transaction(trade_details)
                else:
                    skipped += 1

            print("Trades: Skipped " + str(skipped) + ". Added " + str(added) + ".")
            db.commit()

    except Exception as e:
        print(f"Trades Error: {str(e)}")
    finally:
        await asyncio.sleep(600)  # Update every 10 minutes


async def fetch_and_display_games(client, CHANNEL_ID):
    # Fetch the list of games for the current day using NBA API
    today = date.today().strftime('%Y-%m-%d')
    response = scoreboardv2.ScoreboardV2(game_date=today)

    game_message = db.get_current_day_games()[1]
    
    if response.data_sets:
        try:
            games = response.get_data_frames()[0]

            # Create a formatted message with game information
            formatted_message = "Current Day's NBA Games:\n"
            for index, game in games.iterrows():
                formatted_message += f"{game['GAMECODE']} - {game['GAME_STATUS_TEXT']} ({game['GAME_CLOCK']})\n"

            # Update the message with the list of games
            if bot.game_message != "":
                await bot.game_message.edit(content=formatted_message)
            else:
                # If the message doesn't exist yet, send a new message
                bot.game_message = await client.get_channel(CHANNEL_ID).send(formatted_message)
        except IndexError:
            return
        except Exception as e:
            # Handle any exceptions that might occur while processing the data
            print(f"Error processing NBA data: {e}")
    else:
        # Handle the case when there are no games for the current day
        formatted_message = "No NBA games scheduled for today."

        if bot.game_message is not None:
            await bot.game_message.edit(content=formatted_message)
        else:
            game_message = await client.get_channel(CHANNEL_ID).send(formatted_message)

    await asyncio.sleep(300)  # Update every 5 minutes