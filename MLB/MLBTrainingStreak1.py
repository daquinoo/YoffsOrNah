import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLB;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team URLs for MLB, including historical names
team_base_urls = {
    'Orioles': 'BAL',
    'Tampa Bay Rays': 'TBR',
    'Tampa Bay Devil Rays': 'TBD',
    'Blue Jays': 'TOR',
    'Yankees': 'NYY',
    'Red Sox': 'BOS',
    'Twins': 'MIN',
    'Tigers': 'DET',
    'Cleveland': 'CLE',
    'White Sox': 'CHW',
    'Royals': 'KCR',
    'Astros': 'HOU',
    'Rangers': 'TEX',
    'Mariners': 'SEA',
    'Los Angeles Angels': 'LAA',
    'Anaheim Angels': 'ANA',
    'Athletics': 'OAK',
    'Braves': 'ATL',
    'Phillies': 'PHI',
    'Miami Marlins': 'MIA',
    'Florida Marlins': 'FLA',
    'Mets': 'NYM',
    'Nationals': 'WSN',
    'Montreal Expos': 'MON',
    'Brewers': 'MIL',
    'Cubs': 'CHC',
    'Reds': 'CIN',
    'Pirates': 'PIT',
    'Cardinals': 'STL',
    'Dodgers': 'LAD',
    'Diamondbacks': 'ARI',
    'Padres': 'SDP',
    'Giants': 'SFG',
    'Rockies': 'COL'
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

    tables = soup.find_all('table', {'id': table_id})
    for table in tables:
        if table:
            for row in table.find('tbody').find_all('tr'):
                team_name_cell = row.find('th', {'data-stat': 'team_ID'})
                if team_name_cell:
                    team_name = team_name_cell.text.strip()
                    if team_name_cell.find('strong') or team_name_cell.find('em'):
                        standings.append(team_name)
    
    return standings

def parse_team_stats(html_content, stat_type):
    soup = BeautifulSoup(html_content, 'html.parser')
    table_id = f"team_{stat_type}_gamelogs"
    table = soup.find('table', {'id': table_id})
    game_logs = []

    if table:
        rows = table.find('tbody').find_all('tr')
        start_parsing = False
        for row in rows:
            if start_parsing:
                game_log = {}
                outcome_cell = row.find('td', {'data-stat': 'game_result'})
                if outcome_cell and outcome_cell.text:
                    outcome = outcome_cell.text
                    game_log['win_pct'] = 1 if outcome.startswith('W') else 0
                    if stat_type == 'batting':
                        game_log.update({
                            'hits_pg': row.find('td', {'data-stat': 'H'}).text,
                            'xbh_pg': int(row.find('td', {'data-stat': '2B'}).text) + int(row.find('td', {'data-stat': '3B'}).text) + int(row.find('td', {'data-stat': 'HR'}).text),
                            'runs_pg': row.find('td', {'data-stat': 'R'}).text,
                            'HR_pg': row.find('td', {'data-stat': 'HR'}).text,
                            'RBI_pg': row.find('td', {'data-stat': 'RBI'}).text,
                            'team_BB': row.find('td', {'data-stat': 'BB'}).text,
                            'team_BA': row.find('td', {'data-stat': 'batting_avg'}).text,
                            'team_OBP': row.find('td', {'data-stat': 'onbase_perc'}).text,
                            'team_SLG': row.find('td', {'data-stat': 'slugging_perc'}).text,
                            'team_SB_pg': row.find('td', {'data-stat': 'SB'}).text,
                            'team_CS_pg': row.find('td', {'data-stat': 'CS'}).text,
                        })
                    else:  # pitching
                        game_log.update({
                            'team_H_all': row.find('td', {'data-stat': 'H'}).text,
                            'team_runs_all': row.find('td', {'data-stat': 'R'}).text,
                            'team_HR_all': row.find('td', {'data-stat': 'HR'}).text,
                            'team_SO': row.find('td', {'data-stat': 'SO'}).text,
                            'team_BB_all': row.find('td', {'data-stat': 'BB'}).text,
                            'ERA': row.find('td', {'data-stat': 'earned_run_avg'}).text,
                        })
                    game_logs.append(game_log)
            elif row.find('th', {'aria-label': 'Aug'}):
                start_parsing = True

    return game_logs

def insert_game_logs(year, team_name, game_logs, stat_type):
    for i, game_log in enumerate(game_logs):
        if stat_type == 'batting':
            cursor.execute("""
                INSERT INTO [dbo].[Baseball-Stats] (
                    year, team, games_played, win_pct, div_rnk, lg_rnk, hits_pg, xbh_pg, runs_pg, HR_pg, RBI_pg,
                    team_BB, team_BA, team_OBP, team_SLG, team_SB_pg, team_CS_pg, yoffs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                year, team_name, i + 1, game_log['win_pct'], None, None, game_log['hits_pg'], game_log['xbh_pg'],
                game_log['runs_pg'], game_log['HR_pg'], game_log['RBI_pg'], game_log['team_BB'], game_log['team_BA'],
                game_log['team_OBP'], game_log['team_SLG'], game_log['team_SB_pg'], game_log['team_CS_pg'], 1
            ))
        else:  # pitching
            cursor.execute("""
                UPDATE [dbo].[Baseball-Stats]
                SET team_H_all=?, team_runs_all=?, team_HR_all=?, team_SO=?, team_BB_all=?, ERA=?
                WHERE year=? AND team=? AND games_played=?
            """, (
                game_log['team_H_all'], game_log['team_runs_all'], game_log['team_HR_all'], game_log['team_SO'],
                game_log['team_BB_all'], game_log['ERA'], year, team_name, i + 1
            ))
    conn.commit()

def main():
    years = range(2012, 2013)
    standings_tables = [
        'standings_E', 'standings_W', 'standings_C'
    ]

    for year in years:
        url = f"https://www.baseball-reference.com/leagues/majors/{year}-standings.shtml"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        standings = []
        for table_id in standings_tables:
            standings += parse_standings(soup, table_id)
        
        for team_name in standings:
            team_code = next((code for name, code in team_base_urls.items() if name in team_name), None)
            if team_code:
                for stat_type in ['batting', 'pitching']:
                    team_url = f"https://www.baseball-reference.com/teams/tgl.cgi?team={team_code}&t={stat_type[0]}&year={year}"
                    html_content = fetch_html(team_url)
                    game_logs = parse_team_stats(html_content, stat_type)
                    insert_game_logs(year, team_name, game_logs, stat_type)
            print(f"Finished updating {team_name} for year {year}")

        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
