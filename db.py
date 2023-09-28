from os.path import isfile
from sqlite3 import connect

DB_PATH = "./db/database.db"
BUILD_PATH = "./db/build.sql"

cxn = connect(DB_PATH, check_same_thread=False)
cur = cxn.cursor()

def with_commit(func):
    def inner(*args, **kwargs):
        func(*args, **kwargs)
        commit()
    return inner

@with_commit
def build():
    if isfile(BUILD_PATH):
        scriptexec(BUILD_PATH)

def commit():
    cxn.commit()

def close():
    cxn.close()

def field(command, *values):
    cur.execute(command, tuple(values))

    if (fetch := cur.fetchone()) is not None:
        return fetch[0]
    
def record(command, *values):
    cur.execute(command, tuple(values))

    return cur.fetchone()

def records(command, *values):
    cur.execute(command, tuple(values))

    return cur.fetchall()

def column(command, *values):
    cur.execute(command, tuple(values))

    return [item[0] for item in cur.fetchall()]

def execute(command, *values):
    cur.execute(command, tuple(values))

def multiexec(command, valueset):
    cur.executemany(command, valueset)

def scriptexec(path):
    with open(path, "r", encoding="utf-8") as script:
        cur.executescript(script.read())

# Application specific functions
def add_transaction(transaction):
    execute("INSERT INTO transactions (trade_details) VALUES (?)", transaction)

def get_all_transactions():
    return records("SELECT * FROM transactions")

def add_todays_games(date, game):
    execute("INSERT INTO todays_games (games_date, games) VALUES (?, ?)", date, game)

def update_todays_games(game):
    execute("UPDATE todays_games SET games = ? WHERE games = ?", game)

def get_current_day_games():
    return records("SELECT * FROM todays_games WHERE games_date >= strftime('%s', 'start of day', 'localtime') AND games_date < strftime('%s', 'start of day', '+1 day', 'localtime')")