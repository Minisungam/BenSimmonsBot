import bot
import db

if __name__ == '__main__':
    db.build()
    bot.run_discord_bot()