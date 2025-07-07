import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNFL;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

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

def update_playoff_results(year, playoff_results):
    round_col = {
        "WildCard": "yoffs_rdone",
        "Division": "yoffs_rtwo",
        "ConfChamp": "yoffs_rdthr",
        "SuperBowl": "yoffs_champ"
    }

    for result in playoff_results:
        winner, loser, round_name = result
        round_column = round_col.get(round_name)
        
        cursor.execute(f"""
            UPDATE [dbo].[Football-Stats]
            SET {round_column} = 1
            WHERE year = ? AND team = ?
        """, year, winner)
        
        cursor.execute(f"""
            UPDATE [dbo].[Football-Stats]
            SET {round_column} = 0
            WHERE year = ? AND team = ?
        """, year, loser)
        
    conn.commit()

def fetch_playoff_results(year):
    url = f"https://www.pro-football-reference.com/years/{year}/#all_team_stats"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'id': 'playoff_results'})

    # Check if table is commented out
    if table is None:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        playoff_results_comment = next((comment for comment in comments if 'id="playoff_results"' in comment), None)
        if playoff_results_comment:
            table_soup = BeautifulSoup(playoff_results_comment, 'html.parser')
            table = table_soup.find('table', {'id': 'playoff_results'})

    if table is None:
        print(f"Error: 'playoff_results' table not found for year {year}")
        return []

    playoff_results = []
    for row in table.find('tbody').find_all('tr'):
        week_num = row.find('th', {'data-stat': 'week_num'}).text
        winner = row.find('td', {'data-stat': 'winner'}).text.strip()
        loser = row.find('td', {'data-stat': 'loser'}).text.strip()
        playoff_results.append((winner, loser, week_num))
    
    return playoff_results

def update_playoff_presence(year, teams_in_division):
    cursor.execute(f"""
        UPDATE [dbo].[Football-Stats]
        SET yoffs_rdone = 1
        WHERE year = ? AND team IN ({','.join('?' for _ in teams_in_division)}) AND yoffs_rdone IS NULL
    """, [year] + teams_in_division)
    
    conn.commit()

def main():
    for year in range(2000, 2003):
        playoff_results = fetch_playoff_results(year)
        if playoff_results:
            update_playoff_results(year, playoff_results)
            
            teams_in_division = set(result[0] for result in playoff_results if result[2] == 'Division')
            update_playoff_presence(year, list(teams_in_division))
            
            print(f"Finished updating year {year}")
    for year in range(2000, 2003):
        cursor.execute(f"""
            UPDATE [dbo].[Football-Stats]
            SET yoffs_rdone = 1
            WHERE year = ? AND yoffs_rdone IS NULL AND yoffs_rtwo IS NOT NULL
        """, year)
        conn.commit()
        print(f"Updated playoff presence for teams with byes in year {year}")

if __name__ == "__main__":
    main()
    conn.close()
