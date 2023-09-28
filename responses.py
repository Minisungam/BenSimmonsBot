import random
from nba_api.live.nba.endpoints import scoreboard

def get_response(message: str) -> str:
    p_message = message.lower()

    if p_message == "!roll":
        return ":game_die: You rolled: " + str(random.randint(1, 10)) + " :game_die:"
    
    if p_message == "!help":
        return '```!help - Displays this message\n!roll - Rolls a random number between 1 and 10```'
    
    return None