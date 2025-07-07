import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-NHL;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
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

def parse_table(html_content, table_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table', id=table_id)
    if not tables:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if f'id="{table_id}"' in comment:
                table_soup = BeautifulSoup(comment, 'html.parser')
                tables.extend(table_soup.find_all('table', id=table_id))
    return tables

def parse_standings(html_content, table_id):
    tables = parse_table(html_content, table_id)
    standings = []
    for table in tables:
        if table:
            rows = table.find('tbody').find_all('tr')
            for row in rows:
                team_cell = row.find('th', {'data-stat': 'team_name'})
                if team_cell:
                    team_name = team_cell.text.strip()
                    # Check if the team name contains an asterisk (*)
                    yoffs = 1 if '*' in team_name else 0
                    standings.append({'team': team_name.replace('*', '').strip(), 'yoffs': yoffs})
    return standings

def update_yoffs_data(year, standings):
    for entry in standings:
        try:
            cursor.execute("""
                UPDATE [dbo].[Hockey-Training-Stats]
                SET yoffs = ?
                WHERE team = ? AND year = ?
            """, (entry['yoffs'], entry['team'], year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data for {entry['team']} in {year}: {e}")

def main():
    base_url = "https://www.hockey-reference.com/leagues/NHL_{}.html"
    for year in range(2000, 2024+1):
        if year == 2005:
            continue  # Skip the year 2005
        url = base_url.format(year)
        html_content = fetch_html(url)
        if html_content:
            table_id = 'standings' if year == 2021 else 'standings_EAS'
            east_standings = parse_standings(html_content, table_id)
            west_standings = parse_standings(html_content, 'standings_WES')
            standings = east_standings + west_standings

            if standings:
                update_yoffs_data(year, standings)
                print(f"Playoff data updated successfully for the year {year}.")
            else:
                print(f"No valid data parsed from the HTML for the year {year}.")
        else:
            print(f"Failed to fetch HTML content for the year {year}.")
    conn.close()

if __name__ == "__main__":
    main()
