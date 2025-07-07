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

def update_round_opp(year, team, playoff_results):
    round_mapping = {
        1: "WildCard",
        2: "WildCard",
        3: "WildCard",
        4: "WildCard",
        5: "WildCard",
        6: "WildCard",
        7: "Division",
        8: "ConfChamp",
        9: "SuperBowl"
    }

    # Check if team has a bye week (not in WildCard but in Division)
    has_bye = not any(result for result in playoff_results if result[2] == "WildCard" and (result[0] == team or result[1] == team)) and \
              any(result for result in playoff_results if result[2] == "Division" and (result[0] == team or result[1] == team))

    for game_played in range(1, 10):
        if has_bye and game_played <= 6:
            round_name = "Division"
        elif has_bye and game_played == 7:
            round_name = "ConfChamp"
        elif has_bye and game_played == 8:
            round_name = "SuperBowl"
        else:
            round_name = round_mapping[game_played]

        opponent = None
        for result in playoff_results:
            if result[2] == round_name and (result[0] == team or result[1] == team):
                opponent = result[1] if result[0] == team else result[0]
                break

        if opponent:
            cursor.execute(f"""
                UPDATE [dbo].[Football-Stats]
                SET round_opp = ?
                WHERE year = ? AND team = ? AND games_played = ?
            """, opponent, year, team, game_played)
    
    conn.commit()

def main():
    # Update round_opp for each team and year
    for year in range(2000, 2024):
        playoff_results = fetch_playoff_results(year)
        if not playoff_results:
            continue

        cursor.execute("SELECT DISTINCT team FROM [dbo].[Football-Stats] WHERE year = ?", year)
        teams = [row[0] for row in cursor.fetchall()]
        for team in teams:
            update_round_opp(year, team, playoff_results)
            print(f"Updated round_opp for team {team} in year {year}")

if __name__ == "__main__":
    main()
    conn.close()
