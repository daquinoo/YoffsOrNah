import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};'
                      'Server=tcp:yoffsornah.database.windows.net,1433;'
                      'Database=YoffsOrNah-train-NFL;Uid=danny1phantom;'
                      'Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;'
                      'Connection Timeout=30;')
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

def parse_sacks(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    table_comment = next((comment for comment in comments if 'id="passing"' in comment), None)

    if table_comment:
        table_soup = BeautifulSoup(table_comment, 'html.parser')
        tbody = table_soup.find('table', id='passing').find('tbody')
        return tbody
    else:
        soup = BeautifulSoup(html_content, 'html.parser')
        tbody = soup.find('table', id='passing').find('tbody')
        return tbody

def collect_sacks_data(html_content):
    data = {}
    tbody = parse_sacks(html_content)
    if tbody:
        rows = tbody.find_all('tr')
        for row in rows:
            team_cell = row.find('td', {'data-stat': 'team'})
            if team_cell:
                team_name = team_cell.text.strip()
                games_played_cell = row.find('td', {'data-stat': 'g'})
                sacks_cell = row.find('td', {'data-stat': 'pass_sacked'})
                sackyds_cell = row.find('td', {'data-stat': 'pass_sacked_yds'})
                if games_played_cell and sacks_cell and sackyds_cell:
                    try:
                        games_played = int(games_played_cell.text.strip())
                        sacks = float(sacks_cell.text.strip())
                        sackyds = float(sackyds_cell.text.strip())
                        sacks_all_pg = sacks / games_played if games_played > 0 else 0
                        sackyds_all_pg = sackyds / games_played if games_played > 0 else 0
                        data[team_name] = {
                            'sacks_all_pg': sacks_all_pg,
                            'sackyds_all_pg': sackyds_all_pg
                        }
                    except ValueError:
                        continue
    return data

def update_sacks(data, year):
    for team_name, values in data.items():
        sacks_all_pg = values['sacks_all_pg']
        sackyds_all_pg = values['sackyds_all_pg']
        try:
            cursor.execute("""
                UPDATE [dbo].[Football-Training-Stats]
                SET sacks_all_pg = ?, sackyds_all_pg = ?
                WHERE team = ? AND year = ?
            """, (sacks_all_pg, sackyds_all_pg, team_name, year))
            conn.commit()
            print(f"Updated sacks_all_pg for {team_name}.")
        except Exception as e:
            print(f"Error updating sacks_all_pg for {team_name}: {e}")

def main():
    for year in range(2023, 2023+1):
        url = f"https://www.pro-football-reference.com/years/{year}/#all_team_stats"
        try:
            html_content = fetch_html(url)
            if html_content:
                sacks_data = collect_sacks_data(html_content)
                if sacks_data:
                    update_sacks(sacks_data, year)
                    print(f"Sacks data updated successfully for the year {year}.")
                else:
                    print(f"No valid sacks data parsed from the HTML for the year {year}.")
            else:
                print(f"Failed to retrieve content for the year {year}.")
        except Exception as e:
            print(e)
    conn.close()

if __name__ == "__main__":
    main()

