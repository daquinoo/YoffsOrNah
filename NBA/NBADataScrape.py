import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-base-NBA;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        print("Failed to retrieve the webpage")
        return None

def parse_stats(html_content, table_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    table_comment = next((comment for comment in comments if f'id="{table_id}"' in comment), None)

    if table_comment:
        table_soup = BeautifulSoup(table_comment, 'html.parser')
        tbody = table_soup.find('table', id=table_id).find('tbody')
        return tbody
    else:
        soup = BeautifulSoup(html_content, 'html.parser')
        tbody = soup.find('table', id=table_id).find('tbody')
        return tbody

def parse_standings(html_content, table_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id=table_id)
    standings = {}
    if table:
        rows = table.find('tbody').find_all('tr', class_='full_table')
        for row in rows:
            team_name_elem = row.find('th', {'data-stat': 'team_name'})
            conf_stdg_elem = team_name_elem.find('span', class_='seed')
            cols = row.find_all('td')
            win_pct = float(cols[2].text.strip())
            if team_name_elem and conf_stdg_elem:
                team = re.sub(r'[\*\xa0]', '', team_name_elem.text).strip().split('(')[0].strip()
                conf_stdg = int(re.sub(r'\D', '', conf_stdg_elem.text.strip()))
                standings[team] = {
                    'win_pct': win_pct,
                    'conf_stdg': conf_stdg
                }
    return standings

def collect_team_data(html_content, table_id):
    data = []
    tbody = parse_stats(html_content, table_id)
    if tbody:
        rows = tbody.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if cols:
                team_data = {
                    'year': 2024,
                    'team': cols[0].text.strip().replace('*', ''),
                    'games_played': int(cols[1].text.strip()),
                    'win_pct': None,
                    'conf_stdg': None,
                    'lg_rank': None,
                    'pts_pg': float(cols[23].text.strip()),
                    'opp_pts_pg': None,
                    'threes_pg': float(cols[8].text.strip()),
                    'opp_three_pg': None,
                    'fg_perc': float(cols[5].text.strip()),
                    'opp_fg_perc': None,
                    'oreb_pg': float(cols[15].text.strip()),
                    'opp_oreb_pg': None,
                    'dreb_pg': float(cols[16].text.strip()),
                    'opp_dreb_pg': None,
                    'ast_pg': float(cols[18].text.strip()),
                    'opp_ast_pg': None,
                    'fta_pg': float(cols[13].text.strip()),
                    'opp_fta_pg': None,
                    'ft_perc': float(cols[15].text.strip()),
                    'turnovers_pg': float(cols[21].text.strip()),
                    'opp_to_pg': None,
                    'stls_pg': float(cols[19].text.strip()),
                    'opp_stls_pg': None,
                    'blocks_pg': float(cols[20].text.strip()),
                    'opp_blks_pg': None
                }
                data.append(team_data)
    return data

def collect_opponent_data(html_content, table_id, team_data_list):
    tbody = parse_stats(html_content, table_id)
    if tbody:
        rows = tbody.find_all('tr')
        for row, team_data in zip(rows, team_data_list):
            cols = row.find_all('td')
            if cols:
                team_data['opp_pts_pg'] = float(cols[23].text.strip())
                team_data['opp_three_pg'] = float(cols[8].text.strip())
                team_data['opp_fg_perc'] = float(cols[5].text.strip())
                team_data['opp_oreb_pg'] = float(cols[15].text.strip())
                team_data['opp_dreb_pg'] = float(cols[16].text.strip())
                team_data['opp_ast_pg'] = float(cols[18].text.strip())
                team_data['opp_fta_pg'] = float(cols[13].text.strip())
                team_data['opp_to_pg'] = float(cols[21].text.strip())
                team_data['opp_stls_pg'] = float(cols[19].text.strip())
                team_data['opp_blks_pg'] = float(cols[20].text.strip())
    return team_data_list

def merge_standings(data, standings):
    for team_data in data:
        team = team_data['team']
        if team in standings:
            team_data['win_pct'] = standings[team]['win_pct']
            team_data['conf_stdg'] = standings[team]['conf_stdg']
    return data

def insert_data(data):
    for entry in data:
        try:
            cursor.execute("""
                INSERT INTO [dbo].[Basketball-Stats] (year, team, games_played, win_pct, conf_stdg, lg_rank,
                                                     pts_pg, opp_pts_pg, threes_pg, opp_three_pg, fg_perc, opp_fg_perc,
                                                     oreb_pg, opp_oreb_pg, dreb_pg, opp_dreb_pg, ast_pg, opp_ast_pg,
                                                     fta_pg, opp_fta_pg, ft_perc, turnovers_pg, opp_to_pg, stls_pg, opp_stls_pg, blocks_pg, opp_blks_pg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (entry['year'], entry['team'], entry['games_played'], entry['win_pct'], entry['conf_stdg'], entry['lg_rank'],
                  entry['pts_pg'], entry['opp_pts_pg'], entry['threes_pg'], entry['opp_three_pg'], entry['fg_perc'], entry['opp_fg_perc'],
                  entry['oreb_pg'], entry['opp_oreb_pg'], entry['dreb_pg'], entry['opp_dreb_pg'], entry['ast_pg'], entry['opp_ast_pg'],
                  entry['fta_pg'], entry['opp_fta_pg'], entry['ft_perc'], entry['turnovers_pg'], entry['opp_to_pg'], entry['stls_pg'], entry['opp_stls_pg'], entry['blocks_pg'], entry['opp_blks_pg']))
            conn.commit()
        except Exception as e:
            print(f"Error inserting data for {entry['team']}: {e}")

def main():
    url = "https://www.basketball-reference.com/leagues/NBA_2024.html"
    html_content = fetch_html(url)
    if html_content:
        east_standings = parse_standings(html_content, 'confs_standings_E')
        west_standings = parse_standings(html_content, 'confs_standings_W')
        standings = {**east_standings, **west_standings}

        team_data = collect_team_data(html_content, 'per_game-team')
        opponent_data = collect_opponent_data(html_content, 'per_game-opponent', team_data)
        merged_data = merge_standings(opponent_data, standings)
        
        if merged_data:
            insert_data(merged_data)
            print("Database updated successfully.")
        else:
            print("No valid data parsed from the HTML.")
    else:
        print("Failed to fetch HTML content.")
    conn.close()

if __name__ == "__main__":
    main()
