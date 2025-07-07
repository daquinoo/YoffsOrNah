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

def parse_standings(soup):
    standings = []
    division_rank = 1

    for row in soup.find_all('tr'):
        if 'onecell' in row.get('class', []):
            division_rank = 1  # Reset rank for new division
            continue
        if row.find('th', {'scope': 'row'}):
            team_name_cell = row.find('th', {'scope': 'row'})
            team_name = team_name_cell.text.strip().replace('*', '').replace('+', '')
            win_pct_cell = row.find('td', {'data-stat': 'win_loss_perc'})
            if win_pct_cell:
                win_p = win_pct_cell.text.strip()
                try:
                    win_pct = float(win_p)
                except ValueError:
                    print(f"Error converting win percentage for team {team_name}: {win_p}")
                    continue
                standings.append((team_name, win_pct, division_rank))
                division_rank += 1

    return standings

def insert_data(year, standings):
    for team_name, win_pct, rank in standings:
        cursor.execute("""
            INSERT INTO [dbo].[Football-Training-Stats] (year, team, win_pct, cur_div_rnk)
            VALUES (?, ?, CAST(? AS DECIMAL(10,3)), ?)
        """, (year, team_name, win_pct, rank))
    conn.commit()

def main():
    for year in range(2023, 2023+1):
        url = f"https://www.pro-football-reference.com/years/{year}/#all_team_stats"
        try:
            html_content = fetch_html(url)
            soup = BeautifulSoup(html_content, 'html.parser')

            afc_soup = soup.find('table', {'id': 'AFC'})  # Specific table ID for AFC
            nfc_soup = soup.find('table', {'id': 'NFC'})  # Specific table ID for NFC

            if afc_soup and nfc_soup:
                afc_data = parse_standings(afc_soup)
                nfc_data = parse_standings(nfc_soup)
                insert_data(year, afc_data + nfc_data)
            else:
                print(f"Error: Could not find AFC or NFC tables in the HTML for the year {year}.")
        except Exception as e:
            print(e)

if __name__ == "__main__":
    main()
    conn.close()
