
import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};'
                      'Server=tcp:yoffsornah.database.windows.net,1433;'
                      'Database=YoffsOrNah-train-NBA;Uid=danny1phantom;'
                      'Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;'
                      'Connection Timeout=30;')
cursor = conn.cursor()

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

def fetch_html(url):
    while True:
        try:
            print(f"Fetching URL: {url}")
            api_response: ScrapeApiResponse = scrapfly_client.scrape(scrape_config=ScrapeConfig(
                url=url,
                render_js=True,
                asp=True
            ))
            return api_response.content
        except Exception as e:
            print(f"Scrapfly error: {e}. Retrying...")

def parse_standings(html_content, table_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id=table_id)
    standings = []
    if table:
        rows = table.find('tbody').find_all('tr', class_='full_table')
        for row in rows:
            team_name_elem = row.find('th', {'data-stat': 'team_name'})
            if team_name_elem:
                team_name = team_name_elem.text.strip()
                yoffs = 1 if '*' in team_name else 0
                team_name = re.sub(r'[\*\xa0]', '', team_name).strip().split('(')[0].strip()
                standings.append((team_name, yoffs))
    return standings

def update_yoffs_data(year, standings):
    for team_name, yoffs in standings:
        try:
            cursor.execute("""
                UPDATE [dbo].[Basketball-Predict-Stats]
                SET yoffs = ?
                WHERE team = ? AND year = ?
            """, (yoffs, team_name, year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data for {team_name} in {year}: {e}")

def main():
    for year in range(2000, 2024+1):
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}.html"
        try:
            html_content = fetch_html(url)
            if html_content:
                if 'confs_standings_E' in html_content and 'confs_standings_W' in html_content:
                    east_standings = parse_standings(html_content, 'confs_standings_E')
                    west_standings = parse_standings(html_content, 'confs_standings_W')
                    standings = east_standings + west_standings
                else:
                    east_standings = parse_standings(html_content, 'divs_standings_E')
                    west_standings = parse_standings(html_content, 'divs_standings_W')
                    standings = east_standings + west_standings

                if standings:
                    update_yoffs_data(year, standings)
                    print(f"Playoff data updated successfully for the year {year}.")
                else:
                    print(f"No valid data parsed from the HTML for the year {year}.")
            else:
                print(f"Failed to retrieve content for the year {year}.")
        except Exception as e:
            print(e)
    conn.close()

if __name__ == "__main__":
    main()
