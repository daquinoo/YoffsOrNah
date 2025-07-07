import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNHL;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team URLs for NHL
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
    'Coyotes': 'ARI',
    'Blackhawks': 'CHI',
    'Canucks': 'VAN',
    'Oilers': 'EDM',
    'Kings': 'LAK',
    'Golden Knights': 'VEG',
    'Flames': 'CGY',
    'Kraken': 'SEA',
    'Ducks': 'ANA',
    'Sharks': 'SJS'
}

def fetch_html(url):
    try:
        api_response: ScrapeApiResponse = scrapfly_client.scrape(scrape_config=ScrapeConfig(
            url=url,
            render_js=True,
            asp=True
        ))
        return api_response.content
    except Exception as e:
        print(f"Scrapfly error: {e}")
        raise Exception(f"Failed to retrieve the webpage using Scrapfly: {e}")

def parse_standings(soup, table_id):
    standings = []

    tables = soup.find_all('table', {'id': table_id})
    for table in tables:
        if table:
            for row in table.find('tbody').find_all('tr'):
                team_name_cell = row.find('th', {'data-stat': 'team_name'})
                if team_name_cell:
                    team_name = team_name_cell.text.strip()
                    if team_name.endswith('*'):
                        team_name = team_name.rstrip('*').strip()
                        standings.append(team_name)
    
    return standings

def parse_team_stats(html_content, stat_type):
    soup = BeautifulSoup(html_content, 'html.parser')
    table_id = f"tm_gamelog_{stat_type}"
    table = soup.find('table', {'id': table_id})
    game_logs = []

    if table:
        rows = table.find('tbody').find_all('tr')
        for row in rows[-5:]:  # Last 5 games
            game_log = {}
            outcome_cell = row.find('td', {'data-stat': 'game_outcome'})
            ot_cell = row.find('td', {'data-stat': 'overtimes'})
            if outcome_cell and outcome_cell.text:
                outcome = outcome_cell.text
                game_log['win_pct'] = 1 if outcome == 'W' else 0
                game_log['pts_per_game'] = 2 if outcome == 'W' else (1 if ot_cell and ot_cell.text in ['OT', 'SO'] else 0)
                game_log.update({
                    'goalsfor_pg': row.find('td', {'data-stat': 'goals'}).text,
                    'goalsag_pg': row.find('td', {'data-stat': 'opp_goals'}).text,
                    'shots_og_pg': row.find('td', {'data-stat': 'shots'}).text,
                    'shots_fc_pg': row.find('td', {'data-stat': 'shots_against'}).text,
                    'powerplay_ops': row.find('td', {'data-stat': 'chances_pp'}).text,
                    'pp_ops_against': row.find('td', {'data-stat': 'opp_chances_pp'}).text,
                })
                game_logs.append(game_log)
    
    return game_logs

def insert_game_logs(year, team_name, game_logs, stat_type, start_game_count):
    for i, game_log in enumerate(game_logs):
        cursor.execute("""
            INSERT INTO [dbo].[Hockey-Stats] (
                year, team, games_played, win_pct, conf_stdg, lg_rnk, pts_per_game, goalsfor_pg, goalsag_pg,
                shots_og_pg, shots_fc_pg, powerplay_ops, pp_ops_against, yoffs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            year, team_name, start_game_count + i + 1, game_log['win_pct'], None, None, game_log['pts_per_game'], game_log['goalsfor_pg'],
            game_log['goalsag_pg'], game_log['shots_og_pg'], game_log['shots_fc_pg'], game_log['powerplay_ops'],
            game_log['pp_ops_against'], 1
        ))
    conn.commit()

def main():
    year = 2024
    url = f"https://www.hockey-reference.com/leagues/NHL_{year}.html"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    standings_tables = [
        'standings_EAS', 'standings_WES'
    ]

    standings = []
    for table_id in standings_tables:
        standings += parse_standings(soup, table_id)
    
    for team_name in standings:
        team_code = next((code for name, code in team_base_urls.items() if name in team_name), None)
        if team_code:
            game_count = 0
            for stat_type in ['rs', 'po']:
                team_url = f"https://www.hockey-reference.com/teams/{team_code}/{year}_gamelog.html"
                html_content = fetch_html(team_url)
                game_logs = parse_team_stats(html_content, stat_type)
                insert_game_logs(year, team_name, game_logs, stat_type, game_count)
                game_count += len(game_logs)
        print(f"Finished updating {team_name}")

    print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
