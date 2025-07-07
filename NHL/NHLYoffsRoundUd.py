import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNHL;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

team_nicknames = [
    'Panthers', 'Bruins', 'Maple Leafs', 'Lightning', 'Red Wings', 'Sabres', 'Senators', 'Canadiens',
    'Rangers', 'Hurricanes', 'Islanders', 'Capitals', 'Penguins', 'Flyers', 'Devils', 'Blue Jackets',
    'Stars', 'Jets', 'Avalanche', 'Predators', 'Blues', 'Wild', 'Coyotes', 'Blackhawks', 'Canucks',
    'Oilers', 'Kings', 'Golden Knights', 'Flames', 'Kraken', 'Ducks', 'Sharks', 'Thrashers'
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
        "Final": "yoffs_champ",
        "First Round": "yoffs_rdone", "Conference Quarter-Finals": "yoffs_rdone",
        "Second Round": "yoffs_rtwo", "Conference Semi-Finals": "yoffs_rtwo",
        "Conference Finals": "yoffs_rdthr"
    }

    for result in playoff_results:
        winner, loser, round_name = result
        round_column = round_col.get(round_name)
        
        cursor.execute(f"""
            UPDATE [dbo].[Hockey-Stats]
            SET {round_column} = 1
            WHERE year = ? AND team LIKE ?
        """, year, f"%{winner}%")
        
        cursor.execute(f"""
            UPDATE [dbo].[Hockey-Stats]
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
            winner = links[0].text.strip().split()[-1]
            loser = links[1].text.strip().split()[-1]
        return winner, loser
    except Exception as e:
        print(f"Error extracting team names: {e}")
        return None, None

def fetch_playoff_results(year):
    url = f"https://www.hockey-reference.com/leagues/NHL_{year}.html#all_all_playoffs"
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
        # Skip rows that are headers or irrelevant
        if 'thead' in row.get('class', []) or row.find('td', {'colspan': '5'}):
            continue
        round_elem = row.find('span', {'class': 'tooltip opener'})
        if round_elem:
            round_name = round_elem.text.strip()
            if round_name not in ["Final", "First Round", "Conference Quarter-Finals", "Second Round", "Conference Semi-Finals", "Conference Finals"]:
                continue

            cells = row.find_all('td')
            if cells and len(cells) > 2:  # Ensure there are at least three td elements
                winner, loser = extract_team_names_from_td(cells[2])  # Use the third td for team names
                if winner and loser:
                    playoff_results.append((winner, loser, round_name))
                else:
                    print(f"Error: Could not extract teams from match_info: {cells[2].text.strip()}")
    
    return playoff_results

def main():
    for year in range(2016, 2024+1):
        if year == 2005:
            continue
        playoff_results = fetch_playoff_results(year)
        if playoff_results:
            update_playoff_results(year, playoff_results)
            print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()

