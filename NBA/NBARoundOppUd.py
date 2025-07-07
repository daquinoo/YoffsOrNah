import requests
import re
from bs4 import BeautifulSoup, Comment
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNBA;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
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
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}.html"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'id': 'all_playoffs'})

    # Check if the table is commented out
    if table is None:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        playoffs_comment = next((comment for comment in comments if 'id="all_playoffs"' in comment), None)
        if playoffs_comment:
            table_soup = BeautifulSoup(playoffs_comment, 'html.parser')
            table = table_soup.find('table', {'id': 'all_playoffs'})

    if table is None:
        print(f"Error: 'all_playoffs' table not found for year {year}")
        return []

    playoff_results = []
    for row in table.find('tbody').find_all('tr'):
        # Skip rows that are toggleable or headers
        if 'toggleable' in row.get('class', []) or 'thead' in row.get('class', []):
            continue

        cells = row.find_all('td')
        if len(cells) < 2:
            continue

        round_info = cells[0].get_text().strip()
        match_info = cells[1].get_text(separator=' ').strip()

        # Ensure that the row contains match info
        if 'over' not in match_info:
            continue

        # Use regex to extract team names and scores
        match = re.search(r'(.+?)\s+over\s+(.+?)\s+\((\d+)-(\d+)\)', match_info)
        if not match:
            print(f"Error parsing match_info: {match_info} for year {year}, skipping this row.")
            continue

        try:
            team1 = match.group(1).strip()
            team2 = match.group(2).strip()
            score1 = int(match.group(3).strip())
            score2 = int(match.group(4).strip())
            score_sum = score1 + score2
            playoff_results.append((team1, team2, round_info, score_sum))
        except (IndexError, ValueError) as e:
            print(f"Error extracting data from match_info: {match_info} for year {year}, skipping this row.")
            continue
    
    return playoff_results

def update_round_opp(year, team, playoff_results):
    while True:
        # Get the highest value of games_played in the database for the given team and year with null round_opp
        cursor.execute("""
            SELECT MAX(games_played) FROM [dbo].[Basketball-Stats]
            WHERE year = ? AND team = ? AND round_opp IS NULL
        """, year, team)
        highest_games_played = cursor.fetchone()

        if highest_games_played is None or highest_games_played[0] is None:
            break

        highest_games_played = highest_games_played[0]

        # Initialize the games_to_update dictionary
        games_to_update = {game_played: None for game_played in range(1, highest_games_played + 1)}

        for result in playoff_results:
            team1, team2, round_info, score_sum = result

            if team == team1:
                opponent = team2
            elif team == team2:
                opponent = team1
            else:
                continue

            for game_played in range(highest_games_played, highest_games_played - score_sum, -1):
                if game_played > 0:
                    games_to_update[game_played] = opponent
            highest_games_played -= score_sum

        for game_played, opponent in sorted(games_to_update.items(), reverse=True):
            if opponent:
                cursor.execute("""
                    UPDATE [dbo].[Basketball-Stats]
                    SET round_opp = ?
                    WHERE year = ? AND team = ? AND games_played = ?
                """, opponent, year, team, game_played)
                print(f"Updated year {year}, team {team}, games_played {game_played} with opponent {opponent}")

        # Ensure first 20 games have the same round_opp as game 21 if it exists
        cursor.execute("""
            SELECT round_opp FROM [dbo].[Basketball-Stats]
            WHERE year = ? AND team = ? AND games_played = 21
        """, year, team)
        round_opp_game25 = cursor.fetchone()

        if round_opp_game25 and round_opp_game25[0]:
            round_opp_game25 = round_opp_game25[0]
            for game_played in range(1, 21):
                cursor.execute("""
                    UPDATE [dbo].[Basketball-Stats]
                    SET round_opp = ?
                    WHERE year = ? AND team = ? AND games_played = ?
                """, round_opp_game25, year, team, game_played)
                print(f"Updated year {year}, team {team}, games_played {game_played} with opponent {round_opp_game25}")

    conn.commit()




def main():
    # Update round_opp for each team and year
    for year in range(2000, 2024+1):
        playoff_results = fetch_playoff_results(year)
        if not playoff_results:
            continue

        cursor.execute("SELECT DISTINCT team FROM [dbo].[Basketball-Stats] WHERE year = ?", year)
        teams = [row[0] for row in cursor.fetchall()]
        for team in teams:
            update_round_opp(year, team, playoff_results)
            print(f"Updated round_opp for team {team} in year {year}")

if __name__ == "__main__":
    main()
    conn.close()
