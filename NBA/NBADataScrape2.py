import requests
from bs4 import BeautifulSoup
import pyodbc
import re

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-base-NBA;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception("Failed to retrieve the webpage.")

def parse_conferences(soup):
    conferences = {}

    # Parsing Eastern Conference
    east_table = soup.find('table', id='confs_standings_E')
    if east_table:
        for row in east_table.find('tbody').find_all('tr', class_='full_table'):
            team_name = row.find('th', {'data-stat': 'team_name'}).text.strip().replace('*', '').replace('+', '')
            team_name = re.sub(r'\xa0\(.*\)', '', team_name)  # Remove extra characters
            conferences[team_name] = 'Eastern Conference'
    
    # Parsing Western Conference
    west_table = soup.find('table', id='confs_standings_W')
    if west_table:
        for row in west_table.find('tbody').find_all('tr', class_='full_table'):
            team_name = row.find('th', {'data-stat': 'team_name'}).text.strip().replace('*', '').replace('+', '')
            team_name = re.sub(r'\xa0\(.*\)', '', team_name)  # Remove extra characters
            conferences[team_name] = 'Western Conference'
    
    return conferences

def update_conference_data(year, conferences):
    for team_name, conference in conferences.items():
        print(f"Updating {team_name} to {conference} for year {year}")  # Debug statement
        cursor.execute("""
            UPDATE [dbo].[Basketball-Stats]
            SET conf = ?
            WHERE team = ? AND year = ?
        """, (conference, team_name, year))
    conn.commit()

def main():
    for year in range(2000, 2023):
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}.html"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        conferences = parse_conferences(soup)
        if conferences:
            print(f"Year: {year}, Conferences: {conferences}")  # Debug statement to print parsed conference data
            update_conference_data(year, conferences)
            print(f"Database updated successfully for year {year}.")
        else:
            print(f"Error: Could not find conference tables in the HTML for year {year}.")

if __name__ == "__main__":
    main()
    conn.close()
