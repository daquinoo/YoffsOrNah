import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-NHL;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        print(f"Failed to retrieve the webpage: {url}")
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

def collect_team_data(html_content, table_id, year):
    data = []
    tbody = parse_stats(html_content, table_id)
    if tbody:
        rows = tbody.find_all('tr', class_='full_table')
        for index, row in enumerate(rows):
            team_name_elem = row.find('th', {'data-stat': 'team_name'})
            cols = row.find_all('td')
            if team_name_elem and cols:
                team_data = {
                    'year': year,
                    'team': re.sub(r'[\*\xa0]', '', team_name_elem.text).strip(),
                    'games_played': int(row.find('td', {'data-stat': 'games'}).text),
                    'win_pct': float(row.find('td', {'data-stat': 'wins'}).text) / int(row.find('td', {'data-stat': 'games'}).text),
                    'conf_stdg': index + 1,
                    'pts_per_game': float(row.find('td', {'data-stat': 'points'}).text) / int(row.find('td', {'data-stat': 'games'}).text),
                    'goalsfor_pg': float(row.find('td', {'data-stat': 'goals'}).text) / int(row.find('td', {'data-stat': 'games'}).text),
                    'goalsag_pg': float(row.find('td', {'data-stat': 'opp_goals'}).text) / int(row.find('td', {'data-stat': 'games'}).text)
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
                    'games_played': int(row.find('td', {'data-stat': 'games'}).text),  # Games played from the stats table
                    'save_per': float(row.find('td', {'data-stat': 'save_pct'}).text),
                    'shots_fc_pg': float(row.find('td', {'data-stat': 'shots_against'}).text) / float(row.find('td', {'data-stat': 'games'}).text),
                    'shots_perc': float(row.find('td', {'data-stat': 'shot_pct'}).text),
                    'shots_og_pg': float(row.find('td', {'data-stat': 'shots'}).text) / float(row.find('td', {'data-stat': 'games'}).text),
                    'powerplay_ops': float(row.find('td', {'data-stat': 'chances_pp'}).text) / float(row.find('td', {'data-stat': 'games'}).text),
                    'powerplay_per': float(row.find('td', {'data-stat': 'power_play_pct'}).text)/100,
                    'shg_for_pg': float(row.find('td', {'data-stat': 'goals_sh'}).text) / float(row.find('td', {'data-stat': 'games'}).text),
                    'shg_ag_pg': float(row.find('td', {'data-stat': 'opp_goals_sh'}).text) / float(row.find('td', {'data-stat': 'games'}).text),
                    'pp_ops_against': float(row.find('td', {'data-stat': 'opp_chances_pp'}).text) / float(row.find('td', {'data-stat': 'games'}).text),
                    'penkill_per': float(row.find('td', {'data-stat': 'pen_kill_pct'}).text)/100
                }
        return stats
    else:
        return None

def merge_data(standings, stats, year):
    merged_data = []
    for team in standings.keys():
        entry = {
            'year': year,
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
                INSERT INTO [dbo].[Hockey-Training-Stats] (year, team, games_played, win_pct, conf_stdg, lg_rnk, pts_per_game,
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
    base_url = "https://www.hockey-reference.com/leagues/NHL_{}.html"
    for year in range(2000, 2024+1):
        if year == 2005:
            continue  # Skip the year 2005
        url = base_url.format(year)
        html_content = fetch_html(url)
        if html_content:
            if year == 2021:
                standings = collect_team_data(html_content, 'standings', year)
                # Sort teams by points (pts_per_game) to simulate conference standings
                standings_sorted = sorted(standings, key=lambda x: x['pts_per_game'], reverse=True)
                for i, team in enumerate(standings_sorted):
                    # Assign conference standings
                    team['conf_stdg'] = (i % 16) + 1  # 1-16 for each 'conference'
                standings = {team['team']: team for team in standings_sorted}
            else:
                east_standings = collect_team_data(html_content, 'standings_EAS', year)
                west_standings = collect_team_data(html_content, 'standings_WES', year)
                standings = {team['team']: team for team in east_standings + west_standings}

            stats = collect_stats(html_content, 'stats')

            if standings and stats:
                merged_data = merge_data(standings, stats, year)
                insert_data(merged_data)
                print(f"Database updated successfully for year {year}.")
            else:
                print(f"Failed to parse all required tables for year {year}.")
        else:
            print(f"Failed to fetch HTML content for year {year}.")
    conn.close()



if __name__ == "__main__":
    main()
