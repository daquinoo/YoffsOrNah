import requests
from bs4 import BeautifulSoup
import pyodbc
import re

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-NBA;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content.decode('utf-8')  # Decode the bytes-like object to a string
    else:
        raise Exception("Failed to retrieve the webpage.")

def parse_conferences(soup, table_id):
    conferences = {}

    table = soup.find('table', id=table_id)
    if table:
        for row in table.find('tbody').find_all('tr', class_='full_table'):
            team_name = row.find('th', {'data-stat': 'team_name'}).text.strip().replace('*', '').replace('+', '')
            team_name = re.sub(r'\xa0\(.*\)', '', team_name)  # Remove extra characters
            if 'E' in table_id:
                conferences[team_name] = 'Eastern Conference'
            elif 'W' in table_id:
                conferences[team_name] = 'Western Conference'
    
    return conferences

def parse_divisions(soup, table_id):
    divisions = {}
    current_division = None

    table = soup.find('table', id=table_id)
    if table:
        for row in table.find_all('tr'):
            if 'thead' in row.get('class', []):
                current_division = row.find('th').text.strip()
            elif current_division and row.find('th', {'scope': 'row'}):
                team_name = row.find('th', {'data-stat': 'team_name'}).text.strip().replace('*', '').replace('+', '')
                team_name = re.sub(r'\xa0\(.*\)', '', team_name)  # Remove extra characters
                divisions[team_name] = current_division

    return divisions

def update_conference_data(year, conferences):
    for team_name, conference in conferences.items():
        print(f"Updating {team_name} to {conference} for year {year}")  # Debug statement
        cursor.execute("""
            UPDATE [dbo].[Basketball-Training-Stats]
            SET conf = ?
            WHERE team = ? AND year = ?
        """, (conference, team_name, year))
    conn.commit()

def main():
    for year in range(2000, 2024+1):
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}.html"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if 'confs_standings_E' in html_content and 'confs_standings_W' in html_content:
            east_standings = parse_conferences(soup, 'confs_standings_E')
            west_standings = parse_conferences(soup, 'confs_standings_W')
        else:
            east_standings = parse_divisions(soup, 'divs_standings_E')
            west_standings = parse_divisions(soup, 'divs_standings_W')
        
        standings = {**east_standings, **west_standings}
        if standings:
            print(f"Year: {year}, Standings: {standings}")  # Debug statement to print parsed data
            update_conference_data(year, standings)
            print(f"Database updated successfully for year {year}.")
        else:
            print(f"Error: Could not find standings tables in the HTML for year {year}.")

if __name__ == "__main__":
    main()
    conn.close()
