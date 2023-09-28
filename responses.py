import random

def get_response(message: str) -> str:
    p_message = message.lower()

    if p_message == "!help":
        return '```!help - Displays this message\n!roll - Rolls a random number between 1 and 10\n!abbreviations - Displays a list of abbreviations```'

    if p_message == "!roll":
        return ":game_die: You rolled: " + str(random.randint(1, 10)) + " :game_die:"
    
    if p_message == "!abbreviations":
        return f'**GP** - Games Played\n**GS** - Games Started\n**MIN** - Minutes Played\n**FGM** - Field Goals Made\n**FGA** - Field Goals Attempted\n**FG%** - Field Goal Percentage\n**FG3M** - 3-Point Field Goals Made\n**FG3A** - 3-Point Field Goals Attempted\n**FG3%** - 3-Point Field Goal Percentage\n**FTM** - Free Throws Made\n**FTA** - Free Throws Attempted\n**FT%** - Free Throw Percentage\n**OREB** - Offensive Rebounds\n**DREB** - Defensive Rebounds\n**REB** - Rebounds\n**AST** - Assists\n**STL** - Steals\n**BLK** - Blocks\n**TOV** - Turnovers\n**PF** - Personal Fouls\n**PTS** - Points\n\nFor more information, visit https://www.nba.com/stats/help/glossary/'

    return None