import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNBA;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team URLs
team_base_urls = {
    'Thunder': 'https://www.basketball-reference.com/teams/OKC/2024/gamelog/',
    'Mavericks': 'https://www.basketball-reference.com/teams/DAL/2024/gamelog/',
    'Celtics': 'https://www.basketball-reference.com/teams/BOS/2024/gamelog/',
    'Knicks': 'https://www.basketball-reference.com/teams/NYK/2024/gamelog/',
    'Bucks': 'https://www.basketball-reference.com/teams/MIL/2024/gamelog/',
    'Cavaliers': 'https://www.basketball-reference.com/teams/CLE/2024/gamelog/',
    'Magic': 'https://www.basketball-reference.com/teams/ORL/2024/gamelog/',
    'Pacers': 'https://www.basketball-reference.com/teams/IND/2024/gamelog/',
    '76ers': 'https://www.basketball-reference.com/teams/PHI/2024/gamelog/',
    'Heat': 'https://www.basketball-reference.com/teams/MIA/2024/gamelog/',
    'Bulls': 'https://www.basketball-reference.com/teams/CHI/2024/gamelog/',
    'Hawks': 'https://www.basketball-reference.com/teams/ATL/2024/gamelog/',
    'Nets': 'https://www.basketball-reference.com/teams/BRK/2024/gamelog/',
    'Raptors': 'https://www.basketball-reference.com/teams/TOR/2024/gamelog/',
    'Hornets': 'https://www.basketball-reference.com/teams/CHO/2024/gamelog/',
    'Wizards': 'https://www.basketball-reference.com/teams/WAS/2024/gamelog/',
    'Pistons': 'https://www.basketball-reference.com/teams/DET/2024/gamelog/',
    'Nuggets': 'https://www.basketball-reference.com/teams/DEN/2024/gamelog/',
    'Timberwolves': 'https://www.basketball-reference.com/teams/MIN/2024/gamelog/',
    'Clippers': 'https://www.basketball-reference.com/teams/LAC/2024/gamelog/',
    'Suns': 'https://www.basketball-reference.com/teams/PHO/2024/gamelog/',
    'Pelicans': 'https://www.basketball-reference.com/teams/NOP/2024/gamelog/',
    'Lakers': 'https://www.basketball-reference.com/teams/LAL/2024/gamelog/',
    'Kings': 'https://www.basketball-reference.com/teams/SAC/2024/gamelog/',
    'Warriors': 'https://www.basketball-reference.com/teams/GSW/2024/gamelog/',
    'Rockets': 'https://www.basketball-reference.com/teams/HOU/2024/gamelog/',
    'Jazz': 'https://www.basketball-reference.com/teams/UTA/2024/gamelog/',
    'Grizzlies': 'https://www.basketball-reference.com/teams/MEM/2024/gamelog/',
    'Spurs': 'https://www.basketball-reference.com/teams/SAS/2024/gamelog/',
    'Blazers': 'https://www.basketball-reference.com/teams/POR/2024/gamelog/'
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
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    game_logs = []

    def parse_game_logs(comment, table_id, is_playoff=False):
        if table_id in comment:
            comment_soup = BeautifulSoup(comment, 'html.parser')
            table = comment_soup.find('table', {'id': table_id})
            if table:
                rows = table.find('tbody').find_all('tr')
                for row in rows[-5:] if not is_playoff else rows:
                    if row.get('class') and 'thead' in row.get('class'):
                        continue
                    game_log = {}
                    game_log['pts_pg'] = row.find('td', {'data-stat': 'pts'}).text
                    game_log['opp_pts_pg'] = row.find('td', {'data-stat': 'opp_pts'}).text
                    outcome = row.find('td', {'data-stat': 'game_result'}).text
                    game_log['games_played'] = 1  # Increment by 1 in all cases
                    game_log['win_pct'] = 1 if outcome == 'W' else 0
                    game_log['threes_pg'] = row.find('td', {'data-stat': 'fg3'}).text
                    game_log['opp_three_pg'] = row.find('td', {'data-stat': 'opp_fg3'}).text
                    game_log['fg_perc'] = row.find('td', {'data-stat': 'fg_pct'}).text
                    game_log['opp_fg_perc'] = row.find('td', {'data-stat': 'opp_fg_pct'}).text
                    game_log['oreb_pg'] = row.find('td', {'data-stat': 'orb'}).text
                    game_log['opp_oreb_pg'] = row.find('td', {'data-stat': 'opp_orb'}).text
                    game_log['treb_pg'] = row.find('td', {'data-stat': 'trb'}).text
                    game_log['opp_treb_pg'] = row.find('td', {'data-stat': 'opp_trb'}).text
                    game_log['ast_pg'] = row.find('td', {'data-stat': 'ast'}).text
                    game_log['opp_ast_pg'] = row.find('td', {'data-stat': 'opp_ast'}).text
                    game_log['fta_pg'] = row.find('td', {'data-stat': 'fta'}).text
                    game_log['opp_fta_pg'] = row.find('td', {'data-stat': 'opp_fta'}).text
                    game_log['ft_perc'] = row.find('td', {'data-stat': 'ft_pct'}).text
                    game_log['turnovers_pg'] = row.find('td', {'data-stat': 'tov'}).text
                    game_log['opp_to_pg'] = row.find('td', {'data-stat': 'opp_tov'}).text
                    game_log['stls_pg'] = row.find('td', {'data-stat': 'stl'}).text
                    game_log['opp_stls_pg'] = row.find('td', {'data-stat': 'opp_stl'}).text
                    game_log['blocks_pg'] = row.find('td', {'data-stat': 'blk'}).text
                    game_log['opp_blks_pg'] = row.find('td', {'data-stat': 'opp_blk'}).text

                    game_logs.append(game_log)
    
    for comment in comments:
        parse_game_logs(comment, 'tgl_basic')
        parse_game_logs(comment, 'tgl_basic_playoffs', is_playoff=True)
    
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
    year = 2024
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}.html"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    east_standings = parse_standings(soup, 'confs_standings_E')
    west_standings = parse_standings(soup, 'confs_standings_W')
    
    standings = east_standings + west_standings
    for team_name in standings:
        for key in team_base_urls:
            if key in team_name:
                team_url = team_base_urls[key]
                html_content = fetch_html(team_url)
                game_logs = parse_team_stats(html_content)
                insert_game_logs(year, team_name, game_logs)
                break  # Once a match is found, no need to check further
    
    print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
