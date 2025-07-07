import requests
from bs4 import BeautifulSoup
import pyodbc
import re

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-MLS;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
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
            if row.find('td', {'data-stat': 'team'}):
                team_name = row.find('td', {'data-stat': 'team'}).text.strip().replace('*', '').replace('+', '')
                team_name = re.sub(r'\xa0\(.*\)', '', team_name)  # Remove extra characters
                conferences[team_name] = conference_name
    return conferences

def update_conference_data(year, conferences):
    for team_name, conference in conferences.items():
        print(f"Updating {team_name} to {conference} for year {year}")  # Debug statement
        cursor.execute("""
            UPDATE [dbo].[Soccer-Training-Stats]
            SET conf = ?
            WHERE team = ? AND year = ?
        """, (conference, team_name, year))
    conn.commit()

def main():
    for year in range(2018, 2023+1):
        url = f"https://fbref.com/en/comps/22/{year}/{year}-Major-League-Soccer-Stats"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        eastern_conference = parse_conferences(soup, f'results{year}221Eastern-Conference_overall', 'Eastern Conference')
        western_conference = parse_conferences(soup, f'results{year}221Western-Conference_overall', 'Western Conference')

        conferences = {**eastern_conference, **western_conference}
        if conferences:
            print(f"Year: {year}, Conferences: {conferences}")  # Debug statement to print parsed conference data
            update_conference_data(year, conferences)
            print(f"Database updated successfully for year {year}.")
        else:
            print(f"Error: Could not find conference tables in the HTML for year {year}.")

if __name__ == "__main__":
    main()
    conn.close()
