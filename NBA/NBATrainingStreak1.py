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

# Define team URLs with new relocations and renamings
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

def parse_team_stats(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    game_logs = []

    def safe_get(row, stat, default='0'):
        element = row.find('td', {'data-stat': stat})
        return element.text.strip() if element and element.text.strip() else default
    def parse_game_logs(table, is_playoff=False):
        games_played = 0
        if table:
            rows = table.find('tbody').find_all('tr')
            rows_to_process = rows[-22:] if not is_playoff else rows
            for row in rows_to_process:
                if row.get('class') and 'thead' in row.get('class'):
                    continue
                games_played += 1
                opp_id = safe_get(row, 'opp_id', 'N/A')
                print(f"Opponent ID: {opp_id}")
                print(f"games_played: {games_played}")
                game_log = {
                    'pts_pg': safe_get(row, 'pts'),
                    'opp_pts_pg': safe_get(row, 'opp_pts'),
                    'games_played': 1,
                    'win_pct': 1 if safe_get(row, 'game_result') == 'W' else 0,
                    'threes_pg': safe_get(row, 'fg3'),
                    'opp_three_pg': safe_get(row, 'opp_fg3'),
                    'fg_perc': safe_get(row, 'fg_pct'),
                    'opp_fg_perc': safe_get(row, 'opp_fg_pct'),
                    'oreb_pg': safe_get(row, 'orb'),
                    'opp_oreb_pg': safe_get(row, 'opp_orb'),
                    'treb_pg': safe_get(row, 'trb'),
                    'opp_treb_pg': safe_get(row, 'opp_trb'),
                    'ast_pg': safe_get(row, 'ast'),
                    'opp_ast_pg': safe_get(row, 'opp_ast'),
                    'fta_pg': safe_get(row, 'fta'),
                    'opp_fta_pg': safe_get(row, 'opp_fta'),
                    'ft_perc': safe_get(row, 'ft_pct'),
                    'turnovers_pg': safe_get(row, 'tov'),
                    'opp_to_pg': safe_get(row, 'opp_tov'),
                    'stls_pg': safe_get(row, 'stl'),
                    'opp_stls_pg': safe_get(row, 'opp_stl'),
                    'blocks_pg': safe_get(row, 'blk'),
                    'opp_blks_pg': safe_get(row, 'opp_blk'),
                    'is_playoff': is_playoff
                }
                game_logs.append(game_log)

    # Parse regular season games (not in comments)
    regular_season_table = soup.find('table', {'id': 'tgl_basic'})
    parse_game_logs(regular_season_table)

    # Parse playoff games (in comments)
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        playoff_table = comment_soup.find('table', {'id': 'tgl_basic_playoffs'})
        if playoff_table:
            parse_game_logs(playoff_table, is_playoff=True)

    # Sort game logs to ensure regular season games come first
    game_logs.sort(key=lambda x: x['is_playoff'])
    
    return game_logs

def insert_game_logs(year, team_name, game_logs):
    for i, game_log in enumerate(game_logs):
        cursor.execute("""
            INSERT INTO [dbo].[Basketball-Stats] (
                year, team, games_played, win_pct, pts_pg, opp_pts_pg, threes_pg, opp_three_pg,
                fg_perc, opp_fg_perc, oreb_pg, opp_oreb_pg, treb_pg, opp_treb_pg, ast_pg, opp_ast_pg,
                fta_pg, opp_fta_pg, ft_perc, turnovers_pg, opp_to_pg, stls_pg, opp_stls_pg, blocks_pg, opp_blks_pg, yoffs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            year, team_name, i+1, game_log['win_pct'], game_log['pts_pg'], game_log['opp_pts_pg'],
            game_log['threes_pg'], game_log['opp_three_pg'], game_log['fg_perc'], game_log['opp_fg_perc'],
            game_log['oreb_pg'], game_log['opp_oreb_pg'], game_log['treb_pg'], game_log['opp_treb_pg'],
            game_log['ast_pg'], game_log['opp_ast_pg'], game_log['fta_pg'], game_log['opp_fta_pg'],
            game_log['ft_perc'], game_log['turnovers_pg'], game_log['opp_to_pg'], game_log['stls_pg'],
            game_log['opp_stls_pg'], game_log['blocks_pg'], game_log['opp_blks_pg'], 1  # yoffs set to 1
        ))
    conn.commit()

def main():
    for year in range(2000, 2024 + 1):
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}.html"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if year < 2016:
            standings_tables = ['divs_standings_E', 'divs_standings_W']  # Division standings
        else:
            standings_tables = ['confs_standings_E', 'confs_standings_W']  # Conference standings

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
            html_content = fetch_html(team_url)
            game_logs = parse_team_stats(html_content)
            insert_game_logs(year, team_name, game_logs)
        
        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
