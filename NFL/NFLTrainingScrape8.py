import requests
from bs4 import BeautifulSoup
import pyodbc
import time
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-NFL;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
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

def parse_divisions(soup):
    divisions = {}
    current_division = None

    for row in soup.find_all('tr'):
        if 'thead' in row.get('class', []) and 'onecell' in row.get('class', []):
            current_division = row.find('td', {'data-stat': 'onecell'}).text.strip()
        elif current_division and row.find('th', {'scope': 'row'}):
            team_name_cell = row.find('th', {'scope': 'row'})
            team_name = team_name_cell.text.strip().replace('*', '').replace('+', '')
            divisions[team_name] = current_division

    return divisions

def update_division_data(year, divisions):
    for team_name, division in divisions.items():
        cursor.execute("""
            UPDATE [dbo].[Football-Training-Stats]
            SET div = ?
            WHERE team = ? AND year = ?
        """, (division, team_name, year))
    conn.commit()

def main():
    for year in range(2023, 2023+1):
        url = f"https://www.pro-football-reference.com/years/{year}/"
        try:
            html_content = fetch_html(url)
            soup = BeautifulSoup(html_content, 'html.parser')

            afc_soup = soup.find('table', {'id': 'AFC'})  # Specific table ID for AFC
            nfc_soup = soup.find('table', {'id': 'NFC'})  # Specific table ID for NFC

            if afc_soup and nfc_soup:
                afc_divisions = parse_divisions(afc_soup)
                nfc_divisions = parse_divisions(nfc_soup)
                divisions = {**afc_divisions, **nfc_divisions}
                update_division_data(year, divisions)
            else:
                print(f"Error: Could not find AFC or NFC tables in the HTML for the year {year}.")
        except Exception as e:
            print(e)

if __name__ == "__main__":
    main()
    conn.close()
