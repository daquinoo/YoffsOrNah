from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from bs4 import BeautifulSoup, Comment
import pyodbc
import re

# Initialize Scrapfly client
scrapfly = ScrapflyClient(key='scp-live-c8122bf4379c43f0a0ebd066f2d38b94')

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-MLB;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    try:
        api_response: ScrapeApiResponse = scrapfly.scrape(scrape_config=ScrapeConfig(
            url=url,
            render_js=True,
            asp=True
        ))
        if api_response.status_code == 200:
            return api_response.content
        else:
            print(f"Failed to retrieve the webpage: {url}")
            return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

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
                team_cell = row.find('th', {'data-stat': 'team_ID'})
                if team_cell:
                    team_name = team_cell.text.strip()
                    # Check if the team name is in bold (<strong>) or italics (<em>)
                    yoffs = 1 if team_cell.find('strong') or team_cell.find('em') else 0
                    standings.append({'team': team_name, 'yoffs': yoffs})
    return standings

def update_yoffs_data(year, standings):
    for entry in standings:
        try:
            cursor.execute("""
                UPDATE [dbo].[Baseball-Predict-Stats]
                SET yoffs = ?
                WHERE team = ? AND year = ?
            """, (entry['yoffs'], entry['team'], year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data for {entry['team']} in {year}: {e}")

def main():
    years = range(2000, 2023+1)
    for year in years:
        print(f"Processing year: {year}")
        url = f"https://www.baseball-reference.com/leagues/majors/{year}-standings.shtml"
        
        standings_html = fetch_html(url)
        
        if standings_html:
            standings_data = []
            standings_data.extend(parse_standings(standings_html, 'standings_E'))
            standings_data.extend(parse_standings(standings_html, 'standings_W'))
            standings_data.extend(parse_standings(standings_html, 'standings_C'))

            if standings_data:
                update_yoffs_data(year, standings_data)
                print(f"Playoff data updated successfully for the year {year}.")
            else:
                print(f"No valid data parsed from the HTML for the year {year}.")
        else:
            print(f"Failed to fetch HTML content for the year {year}.")
    
    conn.close()

if __name__ == "__main__":
    main()

