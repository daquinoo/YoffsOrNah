import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-base-MLS;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
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
        rows = tbody.find_all('tr')
        for index, row in enumerate(rows):
            team_name_elem = row.find('td', {'data-stat': 'team'})
            cols = row.find_all('td')
            if team_name_elem and cols:
                team = re.sub(r'[\*\xa0]', '', team_name_elem.text).strip()
                games_played = int(cols[1].text.strip())
                data.append({
                    'year': 2023,
                    'team': team,
                    'games_played': games_played,
                    'win_pct': float(cols[2].text.strip()) / games_played,
                    'conf_stdg': index + 1,
                    'pts_per_game': float(cols[7].text.strip()) / games_played,
                    'gf_pg': float(cols[5].text.strip()) / games_played,
                    'ga_pg': float(cols[6].text.strip()) / games_played
                })
    return data

def insert_data(data):
    for entry in data:
        try:
            cursor.execute("""
                INSERT INTO [dbo].[Soccer-Stats] (year, team, games_played, win_pct, conf_stdg, pts_per_game, gf_pg, ga_pg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (entry['year'], entry['team'], entry['games_played'], entry['win_pct'], entry['conf_stdg'], entry['pts_per_game'], entry['gf_pg'], entry['ga_pg']))
            conn.commit()
        except Exception as e:
            print(f"Error inserting data for {entry['team']}: {e}")

def main():
    url = "https://fbref.com/en/comps/22/2023/2023-Major-League-Soccer-Stats"
    html_content = fetch_html(url)
    if html_content:
        # Standings
        east_standings = collect_team_data(html_content, 'results2023221Eastern-Conference_overall')
        west_standings = collect_team_data(html_content, 'results2023221Western-Conference_overall')
        standings = east_standings + west_standings

        # Insert into the database
        insert_data(standings)
        print("Standings data inserted successfully.")
    else:
        print("Failed to fetch HTML content.")
    conn.close()

if __name__ == "__main__":
    main()
