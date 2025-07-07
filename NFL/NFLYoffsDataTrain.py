import requests
from bs4 import BeautifulSoup
import pyodbc
import time
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNFL;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team base URLs (the year will be dynamically inserted)
team_base_urls = {
    'Bills': 'https://www.pro-football-reference.com/teams/buf/{year}/gamelog/',
    'Dolphins': 'https://www.pro-football-reference.com/teams/mia/{year}/gamelog/',
    'Jets': 'https://www.pro-football-reference.com/teams/nyj/{year}/gamelog/',
    'Patriots': 'https://www.pro-football-reference.com/teams/nwe/{year}/gamelog/',
    'Ravens': 'https://www.pro-football-reference.com/teams/rav/{year}/gamelog/',
    'Browns': 'https://www.pro-football-reference.com/teams/cle/{year}/gamelog/',
    'Steelers': 'https://www.pro-football-reference.com/teams/pit/{year}/gamelog/',
    'Bengals': 'https://www.pro-football-reference.com/teams/cin/{year}/gamelog/',
    'Texans': 'https://www.pro-football-reference.com/teams/htx/{year}/gamelog/',
    'Jaguars': 'https://www.pro-football-reference.com/teams/jax/{year}/gamelog/',
    'Colts': 'https://www.pro-football-reference.com/teams/clt/{year}/gamelog/',
    'Titans': 'https://www.pro-football-reference.com/teams/oti/{year}/gamelog/',
    'Chiefs': 'https://www.pro-football-reference.com/teams/kan/{year}/gamelog/',
    'Raiders': 'https://www.pro-football-reference.com/teams/rai/{year}/gamelog/',
    'Broncos': 'https://www.pro-football-reference.com/teams/den/{year}/gamelog/',
    'Chargers': 'https://www.pro-football-reference.com/teams/sdg/{year}/gamelog/',
    'Cowboys': 'https://www.pro-football-reference.com/teams/dal/{year}/gamelog/',
    'Eagles': 'https://www.pro-football-reference.com/teams/phi/{year}/gamelog/',
    'Giants': 'https://www.pro-football-reference.com/teams/nyg/{year}/gamelog/',
    'Washington': 'https://www.pro-football-reference.com/teams/was/{year}/gamelog/',
    'Lions': 'https://www.pro-football-reference.com/teams/det/{year}/gamelog/',
    'Packers': 'https://www.pro-football-reference.com/teams/gnb/{year}/gamelog/',
    'Vikings': 'https://www.pro-football-reference.com/teams/min/{year}/gamelog/',
    'Bears': 'https://www.pro-football-reference.com/teams/chi/{year}/gamelog/',
    'Buccaneers': 'https://www.pro-football-reference.com/teams/tam/{year}/gamelog/',
    'Saints': 'https://www.pro-football-reference.com/teams/nor/{year}/gamelog/',
    'Falcons': 'https://www.pro-football-reference.com/teams/atl/{year}/gamelog/',
    'Panthers': 'https://www.pro-football-reference.com/teams/car/{year}/gamelog/',
    '49ers': 'https://www.pro-football-reference.com/teams/sfo/{year}/gamelog/',
    'Rams': 'https://www.pro-football-reference.com/teams/ram/{year}/gamelog/',
    'Seahawks': 'https://www.pro-football-reference.com/teams/sea/{year}/gamelog/',
    'Cardinals': 'https://www.pro-football-reference.com/teams/crd/{year}/gamelog/'
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

def parse_standings(soup):
    standings = []

    for row in soup.find_all('tr'):
        if 'onecell' in row.get('class', []):
            continue
        if row.find('th', {'scope': 'row'}):
            team_name_cell = row.find('th', {'scope': 'row'})
            team_name = team_name_cell.text.strip()
            if '*' in team_name or '+' in team_name:
                team_name = team_name.replace('*', '').replace('+', '').strip()
                standings.append(team_name)

    return standings

def fetch_team_game_logs(team_name, url, year):
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    game_logs = []

    def parse_game_logs(table_id, opponent_table_id, is_playoff=False):
        table = soup.find('table', {'id': table_id})
        opponent_table = soup.find('table', {'id': opponent_table_id})
        if table and opponent_table:
            rows = table.find('tbody').find_all('tr')
            opponent_rows = opponent_table.find('tbody').find_all('tr')
            for row, opponent_row in zip(rows[-5:] if not is_playoff else rows, opponent_rows[-5:] if not is_playoff else opponent_rows):
                if row.get('class') and 'thead' in row.get('class'):
                    continue
                game_log = {}
                game_log['pts_pg'] = row.find('td', {'data-stat': 'pts_off'}).text
                game_log['pts_all_pg'] = row.find('td', {'data-stat': 'pts_def'}).text
                outcome = row.find('td', {'data-stat': 'game_outcome'}).text
                game_log['games_played'] = 1  # Increment by 1 in all cases
                game_log['win_pct'] = 1 if outcome == 'W' else 0.5 if outcome == 'T' else 0
                game_log['pass_ypg'] = row.find('td', {'data-stat': 'pass_yds'}).text
                game_log['pass_TD_pg'] = row.find('td', {'data-stat': 'pass_td'}).text
                game_log['int_pg'] = row.find('td', {'data-stat': 'pass_int'}).text
                game_log['sacks_all_pg'] = row.find('td', {'data-stat': 'pass_sacked'}).text
                game_log['sackyds_all_pg'] = row.find('td', {'data-stat': 'pass_sacked_yds'}).text
                game_log['rush_ypg'] = row.find('td', {'data-stat': 'rush_yds'}).text
                game_log['rush_TD_pg'] = row.find('td', {'data-stat': 'rush_td'}).text
                game_log['fga_pg'] = row.find('td', {'data-stat': 'fga'}).text
                fgm = int(row.find('td', {'data-stat': 'fgm'}).text)
                fga = int(game_log['fga_pg'])
                game_log['fgperc_pg'] = fgm / fga if fga != 0 else 0
                xpm = int(row.find('td', {'data-stat': 'xpm'}).text)
                xpa = int(row.find('td', {'data-stat': 'xpa'}).text)
                game_log['xp_perc_pg'] = xpm / xpa if xpa != 0 else 0
                
                # Opponent data
                game_log['pass_yds_all_pg'] = opponent_row.find('td', {'data-stat': 'pass_yds'}).text
                game_log['pass_TD_all_pg'] = opponent_row.find('td', {'data-stat': 'pass_td'}).text
                game_log['int_frc_pg'] = opponent_row.find('td', {'data-stat': 'pass_int'}).text
                game_log['sacks_pg'] = opponent_row.find('td', {'data-stat': 'pass_sacked'}).text
                game_log['sackyds_pg'] = opponent_row.find('td', {'data-stat': 'pass_sacked_yds'}).text
                game_log['rush_yds_all_pg'] = opponent_row.find('td', {'data-stat': 'rush_yds'}).text
                game_log['rush_TD_all_pg'] = opponent_row.find('td', {'data-stat': 'rush_td'}).text
                
                # Additional calculations
                game_log['oyds_p_game'] = float(game_log['rush_ypg']) + float(game_log['pass_ypg'])
                game_log['oyds_all_pg'] = float(game_log['pass_yds_all_pg']) + float(game_log['rush_yds_all_pg'])
                game_log['total_oTD_game'] = float(game_log['rush_TD_pg']) + float(game_log['pass_TD_pg'])
                game_log['oTD_allow_pg'] = float(game_log['pass_TD_all_pg']) + float(game_log['rush_TD_all_pg'])

                game_logs.append(game_log)

    parse_game_logs(f'gamelog{year}', f'gamelog_opp{year}')
    parse_game_logs(f'playoff_gamelog{year}', f'playoff_gamelog_opp{year}', is_playoff=True)

    return game_logs

def insert_game_logs(year, team_name, game_logs):
    for i, game_log in enumerate(game_logs):
        cursor.execute("""
            INSERT INTO [dbo].[Football-Stats] (
                year, team, games_played, win_pct, pts_pg, pts_all_pg,
                pass_ypg, pass_TD_pg, int_pg, sacks_all_pg, sackyds_all_pg,
                rush_ypg, rush_TD_pg, fga_pg, fgperc_pg, xp_perc_pg, pass_yds_all_pg, 
                pass_TD_all_pg, int_frc_pg, sacks_pg, sackyds_pg, rush_yds_all_pg, rush_TD_all_pg,
                oyds_p_game, oyds_all_pg, total_oTD_pg, oTD_allow_pg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            year, team_name, i+1, game_log['win_pct'], game_log['pts_pg'], game_log['pts_all_pg'],
            game_log['pass_ypg'], game_log['pass_TD_pg'], game_log['int_pg'], game_log['sacks_all_pg'],
            game_log['sackyds_all_pg'], game_log['rush_ypg'], game_log['rush_TD_pg'], game_log['fga_pg'],
            game_log['fgperc_pg'], game_log['xp_perc_pg'], game_log['pass_yds_all_pg'], game_log['pass_TD_all_pg'], game_log['int_frc_pg'],
            game_log['sacks_pg'], game_log['sackyds_pg'], game_log['rush_yds_all_pg'], game_log['rush_TD_all_pg'],
            game_log['oyds_p_game'], game_log['oyds_all_pg'], game_log['total_oTD_game'], game_log['oTD_allow_pg']
        ))
    conn.commit()

def main():
    for year in range(2000, 2023 + 1):
        url = f"https://www.pro-football-reference.com/years/{year}/#all_team_stats"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        afc_soup = soup.find('table', {'id': 'AFC'})
        nfc_soup = soup.find('table', {'id': 'NFC'})
        
        if afc_soup and nfc_soup:
            afc_data = parse_standings(afc_soup)
            nfc_data = parse_standings(nfc_soup)
            standings = afc_data + nfc_data
            for team_name in standings:
                for key in team_base_urls:
                    if key in team_name:
                        team_url = team_base_urls[key].format(year=year)
                        game_logs = fetch_team_game_logs(team_name, team_url, year)
                        insert_game_logs(year, team_name, game_logs)
                        break  # Once a match is found, no need to check further
        else:
            print(f"Error: Could not find AFC or NFC tables in the HTML for year {year}.")
        
        # Debug line to indicate the completion of the year
        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
