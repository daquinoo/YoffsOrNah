import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNBA;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

team_nicknames = [
    'Thunder', 'Mavericks', 'Celtics', 'Knicks', 'Bucks', 'Cavaliers', 'Magic', 'Pacers',
    '76ers', 'Heat', 'Bulls', 'Hawks', 'Raptors', 'Wizards', 'Pistons', 'Nuggets',
    'Timberwolves', 'Clippers', 'Suns', 'New Orleans Pelicans', 'Lakers', 'Kings', 'Warriors', 'Rockets',
    'Jazz', 'Spurs', 'Blazers', 'Supersonics', 'Charlotte Hornets', 'New Orleans Hornets', 'Charlotte Bobcats', 'Brooklyn Nets', 'New Jersey Nets'
]

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

def update_playoff_results(year, playoff_results):
    round_col = {
        "Western Conference First Round": "yoffs_rdone",
        "Eastern Conference First Round": "yoffs_rdone",
        "Western Conference Semifinals": "yoffs_rtwo",
        "Eastern Conference Semifinals": "yoffs_rtwo",
        "Western Conference Finals": "yoffs_rdthr",
        "Eastern Conference Finals": "yoffs_rdthr",
        "Finals": "yoffs_champ"
    }

    for result in playoff_results:
        winner, loser, round_name = result
        round_column = round_col.get(round_name)
        
        cursor.execute(f"""
            UPDATE [dbo].[Basketball-Stats]
            SET {round_column} = 1
            WHERE year = ? AND team LIKE ?
        """, year, f"%{winner}%")
        
        cursor.execute(f"""
            UPDATE [dbo].[Basketball-Stats]
            SET {round_column} = 0
            WHERE year = ? AND team LIKE ?
        """, year, f"%{loser}%")
        
    conn.commit()

def extract_team_names_from_td(td):
    try:
        links = td.find_all('a')
        winner = None
        loser = None
        if len(links) == 2:
            winner = links[0].text.strip()
            loser = links[1].text.strip()
            print(f"Extracted - Winner: {winner}, Loser: {loser}")
        return winner, loser
    except Exception as e:
        print(f"Error extracting team names: {e}")
        return None, None

def fetch_playoff_results(year):
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}.html#all_all_playoffs"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'id': 'all_playoffs'})

    # Check if table is commented out
    if table is None:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        playoff_results_comment = next((comment for comment in comments if 'id="all_playoffs"' in comment), None)
        if playoff_results_comment:
            table_soup = BeautifulSoup(playoff_results_comment, 'html.parser')
            table = table_soup.find('table', {'id': 'all_playoffs'})

    if table is None:
        print(f"Error: 'all_playoffs' table not found for year {year}")
        return []

    playoff_results = []
    for row in table.find('tbody').find_all('tr'):
        # Skip rows that do not contain the necessary `strong` elements
        if 'thead' in row.get('class', []):
            continue
        round_elem = row.find('span', {'class': 'tooltip opener'})
        if round_elem is None:
            continue

        round_name = round_elem.find('strong').text.strip()
        if round_name not in ["Western Conference First Round", "Eastern Conference First Round",
                              "Western Conference Semifinals", "Eastern Conference Semifinals",
                              "Western Conference Finals", "Eastern Conference Finals", "Finals"]:
            continue
        
        cells = row.find_all('td')
        if cells and len(cells) > 1:
            winner, loser = extract_team_names_from_td(cells[1])
            if winner and loser:
                playoff_results.append((winner, loser, round_name))
            else:
                print(f"Error: Could not extract teams from match_info: {cells[1].text.strip()}")
    
    return playoff_results

def main():
    for year in range(2000, 2024+1):
        playoff_results = fetch_playoff_results(year)
        if playoff_results:
            print(f"\nPlayoff Results for {year}:")
            for winner, loser, round_name in playoff_results:
                print(f"{round_name}: {winner} defeated {loser}")
            update_playoff_results(year, playoff_results)
            
            print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
