
import requests
from bs4 import BeautifulSoup, Comment
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

def parse_kicking_stats(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    kicking_comment = next((comment for comment in comments if 'id="kicking"' in comment), None)
    
    if kicking_comment:
        kicking_soup = BeautifulSoup(kicking_comment, 'html.parser')
        tbody = kicking_soup.find('table', id='kicking').find('tbody')
    else:
        print("Failed to find the kicking table within the HTML comments.")
        return []
    
    rows = tbody.find_all('tr') if tbody else []
    data = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 21:  # Check for the minimum number of columns
            team_name = cols[0].get_text(strip=True)
            games_played = int(cols[1].get_text(strip=True))  # Ensure we capture the games played as integer

            fga_raw = cols[12].get_text(strip=True)
            fga_pg = float(fga_raw) / games_played if fga_raw else 0  # Compute FGA per game

            fgperc_raw = cols[15].get_text(strip=True).replace('%', '')  # Remove '%' character
            fgperc_pg = float(fgperc_raw) if fgperc_raw else 0

            xpperc_raw = cols[18].get_text(strip=True).replace('%', '')  # Remove '%' character
            xp_perc_pg = float(xpperc_raw) if xpperc_raw else 0

            data.append({
                'team_name': team_name,
                'fga_pg': fga_pg,
                'fgperc_pg': fgperc_pg,
                'xp_perc_pg': xp_perc_pg
            })

    return data

def update_database(data, year):
    for entry in data:
        try:
            cursor.execute("""
                UPDATE [dbo].[Football-Training-Stats]
                SET fga_pg = CAST(? AS DECIMAL(10,3)), fgperc_pg = CAST(? AS DECIMAL(10,3)),
                    xp_perc_pg = CAST(? AS DECIMAL(10,3))
                WHERE team = ? AND year = ?
            """, (entry['fga_pg'], entry['fgperc_pg'], entry['xp_perc_pg'], entry['team_name'], year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data: {e}")

def main():
    for year in range(2023, 2023+1):
        url = f"https://www.pro-football-reference.com/years/{year}/#all_kicking_stats"
        try:
            html_content = fetch_html(url)
            if html_content:
                kicking_data = parse_kicking_stats(html_content)
                if kicking_data:
                    update_database(kicking_data, year)
                    print(f"Kicking data updated successfully for the year {year}.")
                else:
                    print(f"No valid data parsed from the HTML for the year {year}.")
            else:
                print(f"Failed to retrieve content for the year {year}.")
        except Exception as e:
            print(e)
    conn.close()

if __name__ == "__main__":
    main()
