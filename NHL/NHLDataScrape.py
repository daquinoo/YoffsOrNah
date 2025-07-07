import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-base-NHL;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
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

def collect_team_data(html_content, table_id):
    data = []
    tbody = parse_stats(html_content, table_id)
    if tbody:
        rows = tbody.find_all('tr', class_='full_table')
        for index, row in enumerate(rows):
            team_name_elem = row.find('th', {'data-stat': 'team_name'})
            cols = row.find_all('td')
            if team_name_elem and cols:
                team_data = {
                    'year': 2024,
                    'team': re.sub(r'[\*\xa0]', '', team_name_elem.text).strip(),
                    'games_played': int(cols[0].text.strip()),
                    'win_pct': float(cols[1].text.strip()) / int(cols[0].text.strip()),
                    'conf_stdg': index + 1,
                    'pts_per_game': float(cols[4].text.strip()) / int(cols[0].text.strip()),
                    'goalsfor_pg': float(cols[6].text.strip()) / int(cols[0].text.strip()),
                    'goalsag_pg': float(cols[7].text.strip()) / int(cols[0].text.strip())
                }
                data.append(team_data)
    return data

def collect_stats(html_content, table_id):
    data = parse_stats(html_content, table_id)
    if data:
        stats = {}
        rows = data.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if cols:
                team = re.sub(r'[\*\xa0]', '', cols[0].text.strip())
                stats[team] = {
                    'games_played': int(cols[2].text.strip()),  # Games played from the stats table
                    'save_per': float(cols[29].text.strip()),
                    'shots_fc_pg': float(cols[28].text.strip()) / int(cols[2].text.strip()),
                    'shots_perc': float(cols[27].text.strip()),
                    'shots_og_pg': float(cols[26].text.strip()) / int(cols[2].text.strip()),
                    'powerplay_ops': float(cols[17].text.strip()) / int(cols[2].text.strip()),
                    'powerplay_per': float(cols[18].text.strip()),
                    'shg_for_pg': float(row.find('td', {'data-stat': 'goals_sh'}).text) / int(cols[2].text.strip()),
                    'shg_ag_pg': float(row.find('td', {'data-stat': 'opp_goals_sh'}).text) / int(cols[2].text.strip()),
                    'pp_ops_against': float(cols[20].text.strip()) / int(cols[2].text.strip()),
                    'penkill_per': float(cols[21].text.strip())
                }
        return stats
    else:
        return None

def merge_data(standings, stats):
    merged_data = []
    for team in standings.keys():
        entry = {
            'year': 2024,
            'team': team,
            'games_played': standings[team]['games_played'],
            'win_pct': standings[team]['win_pct'],
            'conf_stdg': standings[team]['conf_stdg'],
            'lg_rnk': None,  # Placeholder for league rank, to be calculated later
            'pts_per_game': standings[team]['pts_per_game'],
            'goalsfor_pg': standings[team]['goalsfor_pg'],
            'goalsag_pg': standings[team]['goalsag_pg'],
            'shots_fc_pg': stats[team]['shots_fc_pg'],
            'shots_perc': stats[team]['shots_perc'],
            'shots_og_pg': stats[team]['shots_og_pg'],
            'save_per': stats[team]['save_per'],
            'shg_for_pg': stats[team]['shg_for_pg'],
            'shg_ag_pg': stats[team]['shg_ag_pg'],
            'powerplay_ops': stats[team]['powerplay_ops'],
            'powerplay_per': stats[team]['powerplay_per'],
            'pp_ops_against': stats[team]['pp_ops_against'],
            'penkill_per': stats[team]['penkill_per']
        }
        merged_data.append(entry)
    return merged_data

def insert_data(data):
    for entry in data:
        try:
            cursor.execute("""
                INSERT INTO [dbo].[Hockey-Stats] (year, team, games_played, win_pct, conf_stdg, lg_rnk, pts_per_game,
                                                  goalsfor_pg, goalsag_pg, save_per, shg_for_pg, shg_ag_pg, shots_fc_pg, shots_perc,
                                                  shots_og_pg, powerplay_ops, powerplay_per, pp_ops_against,
                                                  penkill_per)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (entry['year'], entry['team'], entry['games_played'], entry['win_pct'], entry['conf_stdg'], entry['lg_rnk'], 
                  entry['pts_per_game'], entry['goalsfor_pg'], entry['goalsag_pg'], entry['save_per'], entry['shg_for_pg'], entry['shg_ag_pg'], entry['shots_fc_pg'], 
                  entry['shots_perc'], entry['shots_og_pg'], entry['powerplay_ops'], entry['powerplay_per'], entry['pp_ops_against'], 
                  entry['penkill_per']))
            conn.commit()
        except Exception as e:
            print(f"Error inserting data for {entry['team']}: {e}")

def main():
    url = "https://www.hockey-reference.com/leagues/NHL_2024.html"
    html_content = fetch_html(url)
    if html_content:
        east_standings = collect_team_data(html_content, 'standings_EAS')
        west_standings = collect_team_data(html_content, 'standings_WES')
        standings = {team['team']: team for team in east_standings + west_standings}

        stats = collect_stats(html_content, 'stats')

        if standings and stats:
            merged_data = merge_data(standings, stats)
            insert_data(merged_data)
            print("Database updated successfully.")
        else:
            print("Failed to parse all required tables.")
    else:
        print("Failed to fetch HTML content.")
    conn.close()

if __name__ == "__main__":
    main()
