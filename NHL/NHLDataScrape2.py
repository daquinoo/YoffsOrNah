import requests
from bs4 import BeautifulSoup
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
        raise Exception("Failed to retrieve the webpage.")

def parse_conferences(soup, table_id, conference_name):
    conferences = {}
    table = soup.find('table', id=table_id)
    if table:
        for row in table.find('tbody').find_all('tr'):
            if row.find('th', {'scope': 'row'}):
                team_name = row.find('th', {'data-stat': 'team_name'}).text.strip().replace('*', '').replace('+', '')
                team_name = re.sub(r'\xa0\(.*\)', '', team_name)  # Remove extra characters
                conferences[team_name] = conference_name
    return conferences

def update_conference_data(year, conferences):
    for team_name, conference in conferences.items():
        print(f"Updating {team_name} to {conference} for year {year}")  # Debug statement
        cursor.execute("""
            UPDATE [dbo].[Hockey-Stats]
            SET conf = ?
            WHERE team = ? AND year = ?
        """, (conference, team_name, year))
    conn.commit()

def main():
    url = "https://www.hockey-reference.com/leagues/NHL_2024.html"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    east_conference = parse_conferences(soup, 'standings_EAS', 'Eastern Conference')
    west_conference = parse_conferences(soup, 'standings_WES', 'Western Conference')

    conferences = {**east_conference, **west_conference}
    if conferences:
        print(conferences)  # Debug statement to print parsed conference data
        update_conference_data(2024, conferences)
        print("Database updated successfully.")
    else:
        print("Error: Could not find conference tables in the HTML.")

if __name__ == "__main__":
    main()
    conn.close()
