import requests
import re
from bs4 import BeautifulSoup, Comment
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLB;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
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

def fetch_playoff_results(target_year):
    url = f"https://www.baseball-reference.com/postseason/"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'id': 'postseason_series'})

    if table is None:
        print(f"Error: 'postseason_series' table not found.")
        return []

    playoff_results = []
    processing_year = False

    for row in table.find('tbody').find_all('tr'):
        # Skip rows that are headers or separators
        if 'thead' in row.get('class', []):
            continue

        # Get year from the first column
        year_info = row.find('th').get_text()
        year_match = re.search(r'(\d{4})', year_info)
        if not year_match:
            continue
        row_year = int(year_match.group(1))

        if row_year == target_year:
            processing_year = True  # Start processing rows for the target year
        elif row_year < target_year:
            break  # Stop processing if we reach a year earlier than the target year
        else:
            continue  # Skip rows for years greater than the target year

        cells = row.find_all('td')
        if len(cells) < 2:
            continue

        score_info = cells[0].get_text().strip()

        try:
            # Extract the second and third <a> elements which correspond to the team names
            team1_full = row.find_all('a')[1].get_text().strip()
            team2_full = row.find_all('a')[2].get_text().strip()

            # Normalize team names by removing extra information like record, division, and asterisks
            team1 = re.sub(r'\*.*|\(.*\)', '', team1_full).strip()
            team2 = re.sub(r'\*.*|\(.*\)', '', team2_full).strip()

            playoff_results.append((team1, team2, score_info, target_year))
        except (IndexError, ValueError, AttributeError) as e:
            print(f"Error parsing row: {row} for year {target_year}, skipping this row.")
            continue
    
    print(f"Playoff results for year {target_year}: {playoff_results}")
    return playoff_results

def update_round_opp(year, team, playoff_results):
    # Print the playoff_results for debugging purposes
    print(f"Playoff results for year {year}:")
    for result in playoff_results:
        print(result)

    # Check if the team is in the playoff_results
    team_in_playoffs = any(team in (result[0], result[1]) for result in playoff_results)
    
    if not team_in_playoffs:
        print(f"Team {team} not found in playoff results for year {year}. Skipping updates for this team.")
        return  # Skip this team if not found in playoff results

    # Loop through the playoff results in the correct order
    for result in playoff_results:
        team1, team2, score_info, round_year = result

        if team == team1:
            opponent = team2
        elif team == team2:
            opponent = team1
        else:
            continue

        # Get the next highest games_played row that is NULL for round_opp
        cursor.execute("""
            SELECT MAX(games_played) FROM [dbo].[Baseball-Stats]
            WHERE year = ? AND team = ? AND round_opp IS NULL
        """, year, team)
        highest_games_played = cursor.fetchone()

        if highest_games_played is None or highest_games_played[0] is None:
            print(f"No more NULL round_opp values for team {team} in year {year}.")
            break

        highest_games_played = highest_games_played[0]

        # Update the round_opp for this games_played row
        cursor.execute("""
            UPDATE [dbo].[Baseball-Stats]
            SET round_opp = ?
            WHERE year = ? AND team = ? AND games_played = ?
        """, opponent, year, team, highest_games_played)
        print(f"Updated year {year}, team {team}, games_played {highest_games_played} with opponent {opponent}")

    # After all rounds are updated, propagate the last opponent to all lower games_played
    cursor.execute("""
        SELECT MIN(games_played) FROM [dbo].[Baseball-Stats]
        WHERE year = ? AND team = ? AND round_opp IS NOT NULL
    """, year, team)
    lowest_games_played_with_round_opp = cursor.fetchone()

    if lowest_games_played_with_round_opp and lowest_games_played_with_round_opp[0]:
        cursor.execute("""
            SELECT round_opp FROM [dbo].[Baseball-Stats]
            WHERE year = ? AND team = ? AND games_played = ?
        """, year, team, lowest_games_played_with_round_opp[0])
        last_opponent = cursor.fetchone()[0]

        if last_opponent:
            for game_played in range(1, lowest_games_played_with_round_opp[0]):
                cursor.execute("""
                    UPDATE [dbo].[Baseball-Stats]
                    SET round_opp = ?
                    WHERE year = ? AND team = ? AND games_played = ?
                """, last_opponent, year, team, game_played)
                print(f"Updated year {year}, team {team}, games_played {game_played} with opponent {last_opponent}")

    conn.commit()


def main():
    # Update round_opp for each team and year
    for year in range(2023, 2000-1, -1):
        playoff_results = fetch_playoff_results(year)
        if not playoff_results:
            continue

        cursor.execute("SELECT DISTINCT team FROM [dbo].[Baseball-Stats] WHERE year = ?", year)
        teams = [row[0] for row in cursor.fetchall()]
        for team in teams:
            update_round_opp(year, team, playoff_results)
            print(f"Updated round_opp for team {team} in year {year}")

if __name__ == "__main__":
    main()
    conn.close()
