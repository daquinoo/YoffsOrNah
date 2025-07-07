import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNBA;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team base URLs (the year will be dynamically inserted)
team_base_urls = {
    'Thunder': 'https://www.basketball-reference.com/teams/OKC/{year}/gamelog/',
    'Mavericks': 'https://www.basketball-reference.com/teams/DAL/{year}/gamelog/',
    'Celtics': 'https://www.basketball-reference.com/teams/BOS/{year}/gamelog/',
    'Knicks': 'https://www.basketball-reference.com/teams/NYK/{year}/gamelog/',
    'Bucks': 'https://www.basketball-reference.com/teams/MIL/{year}/gamelog/',
    'Cavaliers': 'https://www.basketball-reference.com/teams/CLE/{year}/gamelog/',
    'Magic': 'https://www.basketball-reference.com/teams/ORL/{year}/gamelog/',
    'Pacers': 'https://www.basketball-reference.com/teams/IND/{year}/gamelog/',
    '76ers': 'https://www.basketball-reference.com/teams/PHI/{year}/gamelog/',
    'Heat': 'https://www.basketball-reference.com/teams/MIA/{year}/gamelog/',
    'Bulls': 'https://www.basketball-reference.com/teams/CHI/{year}/gamelog/',
    'Hawks': 'https://www.basketball-reference.com/teams/ATL/{year}/gamelog/',
    'Raptors': 'https://www.basketball-reference.com/teams/TOR/{year}/gamelog/',
    'Wizards': 'https://www.basketball-reference.com/teams/WAS/{year}/gamelog/',
    'Pistons': 'https://www.basketball-reference.com/teams/DET/{year}/gamelog/',
    'Nuggets': 'https://www.basketball-reference.com/teams/DEN/{year}/gamelog/',
    'Timberwolves': 'https://www.basketball-reference.com/teams/MIN/{year}/gamelog/',
    'Clippers': 'https://www.basketball-reference.com/teams/LAC/{year}/gamelog/',
    'Suns': 'https://www.basketball-reference.com/teams/PHO/{year}/gamelog/',
    'Pelicans': 'https://www.basketball-reference.com/teams/NOP/{year}/gamelog/',
    'Lakers': 'https://www.basketball-reference.com/teams/LAL/{year}/gamelog/',
    'Kings': 'https://www.basketball-reference.com/teams/SAC/{year}/gamelog/',
    'Warriors': 'https://www.basketball-reference.com/teams/GSW/{year}/gamelog/',
    'Rockets': 'https://www.basketball-reference.com/teams/HOU/{year}/gamelog/',
    'Jazz': 'https://www.basketball-reference.com/teams/UTA/{year}/gamelog/',
    'Spurs': 'https://www.basketball-reference.com/teams/SAS/{year}/gamelog/',
    'Blazers': 'https://www.basketball-reference.com/teams/POR/{year}/gamelog/',
    'Seattle SuperSonics': 'https://www.basketball-reference.com/teams/SEA/{year}/gamelog/',
    'New Orleans Hornets': 'https://www.basketball-reference.com/teams/NOH/{year}/gamelog/',
    'Charlotte Bobcats': 'https://www.basketball-reference.com/teams/CHA/{year}/gamelog/'
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
    table = soup.find('table', {'id': 'tgl_basic_playoffs'})
    if not table:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if 'id="tgl_basic_playoffs"' in comment:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table', {'id': 'tgl_basic_playoffs'})
                if table:
                    break
    
    if not table:
        return []

    rows = table.find('tbody').find_all('tr')
    game_logs = []
    for row in rows:
        ranker_cell = row.find('th', {'data-stat': 'ranker'})
        opp_id_cell = row.find('td', {'data-stat': 'opp_id'})
        if ranker_cell and opp_id_cell:
            ranker = int(ranker_cell.text.strip())
            opp_id = opp_id_cell.text.strip()
            game_logs.append({'ranker': ranker, 'opp_id': opp_id})
    
    return game_logs

def update_database(year, team_name, game_logs):
    if not game_logs:
        return

    print(f"Updating database for team {team_name}, year {year}")
    game_logs.sort(key=lambda x: x['ranker'], reverse=True)
    rounds = []
    current_opp_id = game_logs[0]['opp_id']
    current_round = []

    for log in game_logs:
        if log['opp_id'] != current_opp_id:
            rounds.insert(0, current_round)  # Prepend current_round to rounds
            current_round = []
            current_opp_id = log['opp_id']
        current_round.append(log)
    
    rounds.insert(0, current_round)  # Prepend the last current_round to rounds
    
    num_rounds = len(rounds)
    
    # Null all fields for games_played 1 through 20
    for games_played in range(1, 21):
        update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
        for field in update_fields:
            print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
            cursor.execute(f"""
                UPDATE [dbo].[Basketball-Stats]
                SET {field} = NULL
                WHERE year = ? AND team = ?
                AND games_played = ?
            """, (year, team_name, games_played))

    for i in range(num_rounds):
        for j in range(len(rounds[i])):
            ranker = rounds[i][j]['ranker']
            games_played = ranker + 20
            if j == 0:
                print(f"Skipping update for highest ranker {ranker} in round {i + 1}")
                continue  # Skip the highest value of ranker for the current round
            
            if i == 0:  # First round (round 1)
                update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
            elif i == 1:  # Second round (round 2)
                update_fields = ['yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
            elif i == 2:  # Third round (round 3)
                update_fields = ['yoffs_rdthr', 'yoffs_champ']
            elif i == 3:  # Fourth round (round 4 - finals)
                update_fields = ['yoffs_champ']
            
            for field in update_fields:
                print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
                cursor.execute(f"""
                    UPDATE [dbo].[Basketball-Stats]
                    SET {field} = NULL
                    WHERE year = ? AND team = ?
                    AND games_played = ?
                """, (year, team_name, games_played))

    conn.commit()
    print(f"Database updated for team {team_name}, year {year}")


def main():
    for year in range(2000, 2024+1):
        print(f"Processing year {year}")
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}.html"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        standings_tables = [
            'confs_standings_E', 'confs_standings_W',  # Conference standings
            'divs_standings_E', 'divs_standings_W'     # Division standings
        ]

        standings = []
        for table_id in standings_tables:
            standings += parse_standings(soup, table_id)
        
        for team_name in standings:
            if team_name == "Charlotte Hornets":
                if year <= 2002:
                    team_url = 'https://www.basketball-reference.com/teams/CHH/{year}/gamelog/'.format(year=year)
                else:
                    team_url = 'https://www.basketball-reference.com/teams/CHO/{year}/gamelog/'.format(year=year)
            elif " Nets" in team_name:
                if year > 2012:
                    team_url = 'https://www.basketball-reference.com/teams/BRK/{year}/gamelog/'.format(year=year)
                else:
                    team_url = 'https://www.basketball-reference.com/teams/NJN/{year}/gamelog/'.format(year=year)
            elif "Grizzlies" in team_name:
                if year > 2001:
                    team_url = 'https://www.basketball-reference.com/teams/MEM/{year}/gamelog/'.format(year=year)
                else:
                    team_url = 'https://www.basketball-reference.com/teams/VAN/{year}/gamelog/'.format(year=year)
            else:
                for key in team_base_urls:
                    if key in team_name:
                        team_url = team_base_urls[key].format(year=year)
            print(f"Fetching game logs for team: {team_name} from URL: {team_url}")
            html_content = fetch_html(team_url)
            team_soup = BeautifulSoup(html_content, 'html.parser')
            game_logs = parse_gamelog(team_soup)
            update_database(year, team_name, game_logs)
        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
