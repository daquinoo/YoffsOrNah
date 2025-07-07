import requests
from bs4 import BeautifulSoup
import pyodbc
import re

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-base-MLB;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception("Failed to retrieve the webpage.")

def parse_divisions(soup, table_id, league_prefix):
    divisions = {}
    tables = soup.find_all('table', id=table_id)

    for i, table in enumerate(tables):
        league = 'AL' if i % 2 == 0 else 'NL'  # Alternate between AL and NL
        division = f"{league_prefix} {league}"

        rows = table.find('tbody').find_all('tr')
        for row in rows:
            if row.find('th', {'scope': 'row'}):
                team_name = row.find('th', {'data-stat': 'team_ID'}).text.strip().replace('*', '').replace('+', '')
                team_name = re.sub(r'\xa0\(.*\)', '', team_name)  # Remove extra characters
                divisions[team_name] = division

    return divisions

def update_division_data(year, divisions):
    for team_name, division in divisions.items():
        print(f"Updating {team_name} to {division} for year {year}")  # Debug statement
        cursor.execute("""
            UPDATE [dbo].[Baseball-Stats]
            SET div = ?
            WHERE team = ? AND year = ?
        """, (division, team_name, year))
    conn.commit()

def main():
    url = "https://www.baseball-reference.com/leagues/majors/2023-standings.shtml"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    al_east = parse_divisions(soup, 'standings_E', 'East')
    al_central = parse_divisions(soup, 'standings_C', 'Central')
    al_west = parse_divisions(soup, 'standings_W', 'West')

    divisions = {**al_east, **al_central, **al_west}
    if divisions:
        print(divisions)  # Debug statement to print parsed division data
        update_division_data(2023, divisions)
        print("Database updated successfully.")
    else:
        print("Error: Could not find standings tables in the HTML.")

if __name__ == "__main__":
    main()
    conn.close()
