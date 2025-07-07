import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Initialize Scrapfly client with your API key
scrapfly = ScrapflyClient(key='scp-live-c8122bf4379c43f0a0ebd066f2d38b94')

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-MLS;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    api_response: ScrapeApiResponse = scrapfly.scrape(scrape_config=ScrapeConfig(
        url=url,
        render_js=True,
        asp=True
    ))
    if api_response.status_code == 200:
        return api_response.content
    else:
        print(f"Failed to retrieve the webpage: {api_response.status_code}")
        return None

def parse_stats(html_content, table_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    table_comment = next((comment for comment in comments if f'id="{table_id}"' in comment), None)

    if table_comment:
        table_soup = BeautifulSoup(table_comment, 'html.parser')
        tbody = table_soup.find('table', id=table_id).find('tbody')
        return tbody
    else:
        tbody = soup.find('table', id=table_id).find('tbody')
        return tbody

def collect_team_data(html_content, table_id, year):
    data = []
    tbody = parse_stats(html_content, table_id)
    if tbody:
        rows = tbody.find_all('tr')
        for index, row in enumerate(rows):
            team_name_elem = row.find('td', {'data-stat': 'team'})
            rank_elem = row.find('th', {'class': 'right playoff'})
            yoffs = 1 if rank_elem else 0
            cols = row.find_all('td')
            if team_name_elem and cols:
                team = re.sub(r'[\*\xa0]', '', team_name_elem.text).strip()
                data.append({
                    'year': year,
                    'team': team,
                    'yoffs': yoffs
                })
    return data

def update_yoffs_data(data):
    for entry in data:
        try:
            cursor.execute("""
                UPDATE [dbo].[Soccer-Predict-Stats]
                SET yoffs = ?
                WHERE team = ? AND year = ?
            """, (entry['yoffs'], entry['team'], entry['year']))
            conn.commit()
        except Exception as e:
            print(f"Error updating data for {entry['team']} in {entry['year']}: {e}")

def main():
    for year in range(2018, 2023+1):
        url = f"https://fbref.com/en/comps/22/{year}/{year}-Major-League-Soccer-Stats"
        html_content = fetch_html(url)
        if html_content:
            east_standings = collect_team_data(html_content, f'results{year}221Eastern-Conference_overall', year)
            west_standings = collect_team_data(html_content, f'results{year}221Western-Conference_overall', year)
            standings = east_standings + west_standings
            update_yoffs_data(standings)
            print(f"Standings data for {year} updated successfully.")
        else:
            print(f"Failed to fetch HTML content for {year}.")
    conn.close()

if __name__ == "__main__":
    main()


