import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNHL;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team base URLs (the year will be dynamically inserted)
team_base_urls = {
    'Panthers': 'FLA',
    'Bruins': 'BOS',
    'Maple Leafs': 'TOR',
    'Lightning': 'TBL',
    'Red Wings': 'DET',
    'Sabres': 'BUF',
    'Senators': 'OTT',
    'Canadiens': 'MTL',
    'Rangers': 'NYR',
    'Hurricanes': 'CAR',
    'Islanders': 'NYI',
    'Capitals': 'WSH',
    'Penguins': 'PIT',
    'Flyers': 'PHI',
    'Devils': 'NJD',
    'Blue Jackets': 'CBJ',
    'Stars': 'DAL',
    'Jets': 'WPG',
    'Avalanche': 'COL',
    'Predators': 'NSH',
    'Blues': 'STL',
    'Wild': 'MIN',
    'Arizona Coyotes': 'ARI',
    'Phoenix Coyotes': 'PHX',
    'Blackhawks': 'CHI',
    'Canucks': 'VAN',
    'Oilers': 'EDM',
    'Kings': 'LAK',
    'Golden Knights': 'VEG',
    'Flames': 'CGY',
    'Kraken': 'SEA',
    'Anaheim Ducks': 'ANA',
    'Mighty Ducks of Anaheim': 'MDA',
    'Sharks': 'SJS',
    'Thrashers': 'ATL'
}

def fetch_html(url):
    while True:
        try:
            print(f"Fetching URL: {url}")
            api_response: ScrapeApiResponse = scrapfly_client.scrape(scrape_config=ScrapeConfig(
                url=url,
                render_js=True,
                asp=True
            ))
            return api_response.content
        except Exception as e:
            print(f"Scrapfly error: {e}. Retrying...")

def parse_standings(soup, table_id):
    standings = []
    table = soup.find('table', {'id': table_id})
    if table:
        print(f"Parsing standings from table: {table_id}")
        for row in table.find('tbody').find_all('tr'):
            team_name_cell = row.find('th', {'data-stat': 'team_name'})
            if team_name_cell:
                team_name = team_name_cell.text.strip()
                team_name = re.sub(r'\(\d+\)', '', team_name).strip()  # Remove (4) or any number in parentheses
                if '*' in team_name or '+' in team_name:
                    team_name = team_name.replace('*', '').replace('+', '').strip()
                    standings.append(team_name)
    return standings

def parse_gamelog(soup):
    table = soup.find('table', {'id': 'tm_gamelog_po'})
    if not table:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if 'id="tm_gamelog_po"' in comment:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table', {'id': 'tm_gamelog_po'})
                if table:
                    break
    
    if not table:
        print("No playoff game log table found.")
        return []

    print("Parsing playoff game log table.")
    rows = table.find('tbody').find_all('tr')
    game_logs = []
    for row in rows:
        if 'thead' in row.get('class', []):
            continue  # Skip separator rows
        games_cell = row.find('th', {'data-stat': 'games'})
        opp_name_cell = row.find('td', {'data-stat': 'opp_name'})
        if games_cell and opp_name_cell:
            games = int(games_cell.text.strip())
            opp_name = opp_name_cell.text.strip()
            game_logs.append({'games': games, 'opp_name': opp_name})
    return game_logs

def update_database(year, team_name, game_logs, qualifying):
    if not game_logs:
        return

    print(f"Updating database for team {team_name}, year {year} (Qualifying: {qualifying})")
    game_logs.sort(key=lambda x: x['games'], reverse=True)
    rounds = []
    current_opp_name = game_logs[0]['opp_name']
    current_round = []

    for log in game_logs:
        if log['opp_name'] != current_opp_name:
            rounds.insert(0, current_round)  # Prepend current_round to rounds
            current_round = []
            current_opp_name = log['opp_name']
        current_round.append(log)
    
    rounds.insert(0, current_round)  # Prepend the last current_round to rounds
    
    num_rounds = len(rounds)
    print(f"Number of playoff rounds: {num_rounds}")
    
    # Null all fields for games_played 1 through 5
    for games_played in range(1, 21):
        update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
        for field in update_fields:
            print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
            cursor.execute(f"""
                UPDATE [dbo].[Hockey-Stats]
                SET {field} = NULL
                WHERE year = ? AND team = ?
                AND games_played = ?
            """, (year, team_name, games_played))

    # Handle the special case for non-qualifying teams in 2020
    if year == 2020 and not qualifying and num_rounds >= 3 and len(rounds[0]) == 1 and len(rounds[1]) == 1 and len(rounds[2]) == 1:
        for i in range(3):
            for log in rounds[i]:
                games = log['games']
                games_played = games + 20
                update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
                for field in update_fields:
                    print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
                    cursor.execute(f"""
                        UPDATE [dbo].[Hockey-Stats]
                        SET {field} = NULL
                        WHERE year = ? AND team = ?
                        AND games_played = ?
                    """, (year, team_name, games_played))
        # Remove the first three rounds after handling them
        rounds = rounds[3:]
        num_rounds -= 3

    # Process remaining playoff rounds
    for i in range(num_rounds):
        for j in range(len(rounds[i])):
            games = rounds[i][j]['games']
            games_played = games + 20
            if j == 0 and not (qualifying and i == 0):
                print(f"Skipping update for highest games {games} in round {i + 1}")
                continue  # Skip the highest value of games for the current round
            
            if qualifying and i == 0:  # Qualifying round treated as non-playoff games
                update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
            elif (qualifying and i == 1) or (not qualifying and i == 0):  # First round of playoffs
                update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
            elif (qualifying and i == 2) or (not qualifying and i == 1):  # Second round of playoffs
                update_fields = ['yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
            elif (qualifying and i == 3) or (not qualifying and i == 2):  # Third round of playoffs
                update_fields = ['yoffs_rdthr', 'yoffs_champ']
            elif (qualifying and i == 4) or (not qualifying and i == 3):  # Fourth round of playoffs (finals)
                update_fields = ['yoffs_champ']
            
            for field in update_fields:
                print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
                cursor.execute(f"""
                    UPDATE [dbo].[Hockey-Stats]
                    SET {field} = NULL
                    WHERE year = ? AND team = ?
                    AND games_played = ?
                """, (year, team_name, games_played))

    conn.commit()
    print(f"Database updated for team {team_name}, year {year}")

def main():
    for year in range(2016, 2024 + 1):
        print(f"Processing year {year}")
        url = f"https://www.hockey-reference.com/leagues/NHL_{year}.html"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')

        if year == 2021:
            standings_tables = ['standings']
        else:
            standings_tables = ['standings_EAS', 'standings_WES']

        standings = []
        for table_id in standings_tables:
            print(f"Parsing standings from table: {table_id}")
            standings += parse_standings(soup, table_id)

        # Handle the special case for 2020
        qualifying_teams = []
        if year == 2020:
            qualifying_teams_table = soup.find('table', {'id': 'all_playoffs'})
            if qualifying_teams_table:
                for row in qualifying_teams_table.find('tbody').find_all('tr'):
                    round_type = row.find('span', {'class': 'tooltip opener'})
                    if round_type and 'Qualifying Round' in round_type.text:
                        team_name_cell = row.find_all('td')[2]  # The cell containing team names is the third <td>
                        if team_name_cell:
                            team_links = team_name_cell.find_all('a')
                            if len(team_links) >= 2:
                                team_name_1 = team_links[0].text.strip()
                                team_name_2 = team_links[1].text.strip()
                                qualifying_teams.append(team_name_1)
                                qualifying_teams.append(team_name_2)
                                print(f"Found qualifying teams: {team_name_1}, {team_name_2}")

        for team_name in standings:
            for key in team_base_urls:
                if key in team_name:
                    team_abbr = team_base_urls[key]
                    team_url = f"https://www.hockey-reference.com/teams/{team_abbr}/{year}_gamelog.html"
                    print(f"Fetching game logs for team: {team_name} from URL: {team_url}")
                    html_content = fetch_html(team_url)
                    team_soup = BeautifulSoup(html_content, 'html.parser')
                    game_logs = parse_gamelog(team_soup)
                    # Special handling for 2020 qualifying round
                    qualifying = year == 2020 and team_name in qualifying_teams
                    print(f"Team {team_name} is qualifying: {qualifying}")
                    update_database(year, team_name, game_logs, qualifying)
        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()

