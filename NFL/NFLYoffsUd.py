import requests
from bs4 import BeautifulSoup
import pyodbc
import time
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-NFL;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

def fetch_html(url):
    try:
        api_response: ScrapeApiResponse = scrapfly_client.scrape(scrape_config=ScrapeConfig(
            url=url,
            render_js=True,
            asp=True
        ))
        return api_response.content
    except Exception as e:
        print(f"Scrapfly error: {e}")
        raise Exception(f"Failed to retrieve the webpage using Scrapfly: {e}")

def parse_standings(soup):
    standings = []

    for row in soup.find_all('tr'):
        if row.find('th', {'scope': 'row'}):
            team_name_cell = row.find('th', {'scope': 'row'})
            team_name = team_name_cell.text.strip()
            yoffs = 1 if '*' in team_name or '+' in team_name else 0
            team_name = team_name.replace('*', '').replace('+', '').strip()

            standings.append((team_name, yoffs))

    return standings

def update_yoffs_data(year, standings):
    for team_name, yoffs in standings:
        try: # or training-stats
            cursor.execute("""
                UPDATE [dbo].[Football-Predict-Stats] 
                SET yoffs = ?
                WHERE team = ? AND year = ?
            """, (yoffs, team_name, year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data for {team_name} in {year}: {e}")

def main():
    for year in range(2000, 2023+1):
        url = f"https://www.pro-football-reference.com/years/{year}/#all_team_stats"
        try:
            html_content = fetch_html(url)
            soup = BeautifulSoup(html_content, 'html.parser')

            afc_soup = soup.find('table', {'id': 'AFC'})  # Specific table ID for AFC
            nfc_soup = soup.find('table', {'id': 'NFC'})  # Specific table ID for NFC

            if afc_soup and nfc_soup:
                afc_data = parse_standings(afc_soup)
                nfc_data = parse_standings(nfc_soup)
                update_yoffs_data(year, afc_data + nfc_data)
                print(f"Playoff data updated successfully for the year {year}.")
            else:
                print(f"Error: Could not find AFC or NFC tables in the HTML for the year {year}.")
        except Exception as e:
            print(e)

if __name__ == "__main__":
    main()
    conn.close()

