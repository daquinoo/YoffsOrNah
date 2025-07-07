import requests
from bs4 import BeautifulSoup
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

def parse_divisions(soup, table_id):
    divisions = {}
    table = soup.find('table', id=table_id)
    current_division = None

    if table:
        for row in table.find_all('tr'):
            if 'thead' in row.get('class', []):
                current_division = row.find('td').text.strip()
            elif current_division and row.find('th', {'scope': 'row'}):
                team_name = row.find('th', {'data-stat': 'team_name'}).text.strip().replace('*', '').replace('+', '')
                team_name = re.sub(r'\xa0\(.*\)', '', team_name)  # Remove extra characters
                divisions[team_name] = current_division

    return divisions

def update_conference_data(year, conferences):
    for team_name, conference in conferences.items():
        print(f"Updating {team_name} to {conference} for year {year}")  # Debug statement
        cursor.execute("""
            UPDATE [dbo].[Hockey-Training-Stats]
            SET conf = ?
            WHERE team = ? AND year = ?
        """, (conference, team_name, year))
    conn.commit()

def main():
    for year in range(2000, 2024+1):
        if year == 2005:
            continue  # Skip the year 2005
        
        url = f"https://www.hockey-reference.com/leagues/NHL_{year}.html"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')

        if year == 2021:
            divisions = parse_divisions(soup, 'standings')
            conferences = divisions
        else:
            east_conference = parse_conferences(soup, 'standings_EAS', 'Eastern Conference')
            west_conference = parse_conferences(soup, 'standings_WES', 'Western Conference')
            conferences = {**east_conference, **west_conference}

        if conferences:
            print(f"Year: {year}, Conferences: {conferences}")  # Debug statement to print parsed conference data
            update_conference_data(year, conferences)
            print(f"Database updated successfully for year {year}.")
        else:
            print(f"Error: Could not find standings tables in the HTML for year {year}.")

if __name__ == "__main__":
    main()
    conn.close()
