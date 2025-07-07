import requests
from bs4 import BeautifulSoup
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLS;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team URLs for MLS
team_base_urls = {
    'FC Cincinnati': 'e9ea41b2',
    'Orlando City': '46ef01d0',
    'D.C. United': '44117292',
    'Crew': '529ba333',
    'Philadelphia': '46024eeb',
    'NE Revolution': '3c079def',
    'Atlanta Utd': '1ebc1a5b',
    'Nashville': '35f1b818',
    'NY Red Bulls': '69a0fb10',
    'Charlotte': 'eb57545a',
    'CF Mon': 'fc22273c',
    'NYCFC': '64e81410',
    'Fire': 'f9940243',
    'Inter Miami': 'cb8b86a2',
    'Toronto FC': '130f43fa',
    'St. Louis': 'bd97ac1f',
    'Seattle': '6218ebd4',
    'LAFC': '81d817a3',
    'Dynamo': '0d885416',
    'RSL': 'f7d86a43',
    'Vancouver W\'caps': 'ab41cb90',
    'FC Dallas': '15cf8f40',
    'Sporting KC': '4acb0537',
    'SJ Earthquakes': 'ca460650',
    'Portland Timbers': 'd076914e',
    'Minnesota Utd': '99ea75a6',
    'Austin': 'b918956d',
    'LA Galaxy': 'd8b46897',
    'Rapids': '415b4465',
    'Montreal': 'fc22273c'  # Added Montreal Impact
}

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

def update_round_opp_from_gamelog(year, team_name, team_id):
    url = f"https://fbref.com/en/squads/{team_id}/{year}/matchlogs/c22/schedule/"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    table = soup.find('table', {'id': 'matchlogs_for'})
    
    if not table:
        print(f"No matchlog table found for team {team_name} in year {year}.")
        return

    rows = table.find('tbody').find_all('tr')[::-1]  # Reverse the order to start from the last row
    highest_games_played = None

    for row in rows:
        # Skip rows with class "spacer partial_table"
        if 'spacer partial_table' in row.get('class', []):
            continue

        round_type = row.find('td', {'data-stat': 'round'}).get_text().strip()

        if "Regular Season" in round_type:
            print(f"Regular season reached for {team_name} in {year}. Stopping updates.")
            break

        opponent_cell = row.find('td', {'data-stat': 'opponent'})
        opponent_name = opponent_cell.get_text().strip() if opponent_cell else None

        if opponent_name:
            # Get the highest games_played with a NULL round_opp
            if highest_games_played is None:
                cursor.execute("""
                    SELECT MAX(games_played) FROM [dbo].[Soccer-Stats]
                    WHERE year = ? AND team = ? AND round_opp IS NULL
                """, year, team_name)
                highest_games_played = cursor.fetchone()[0]

            if highest_games_played is None or highest_games_played <= 0:
                print(f"No more NULL round_opp values for {team_name} in year {year}.")
                break

            # Update the round_opp for this games_played row
            cursor.execute("""
                UPDATE [dbo].[Soccer-Stats]
                SET round_opp = ?
                WHERE year = ? AND team = ? AND games_played = ?
            """, opponent_name, year, team_name, highest_games_played)
            print(f"Updated year {year}, team {team_name}, games_played {highest_games_played} with opponent {opponent_name}")

            highest_games_played -= 1

    # Propagate the last opponent to all lower games_played
    cursor.execute("""
        SELECT MIN(games_played) FROM [dbo].[Soccer-Stats]
        WHERE year = ? AND team = ? AND round_opp IS NOT NULL
    """, year, team_name)
    lowest_games_played_with_round_opp = cursor.fetchone()

    if lowest_games_played_with_round_opp and lowest_games_played_with_round_opp[0]:
        cursor.execute("""
            SELECT round_opp FROM [dbo].[Soccer-Stats]
            WHERE year = ? AND team = ? AND games_played = ?
        """, year, team_name, lowest_games_played_with_round_opp[0])
        last_opponent = cursor.fetchone()[0]

        if last_opponent:
            for game_played in range(1, lowest_games_played_with_round_opp[0]):
                cursor.execute("""
                    UPDATE [dbo].[Soccer-Stats]
                    SET round_opp = ?
                    WHERE year = ? AND team = ? AND games_played = ?
                """, last_opponent, year, team_name, game_played)
                print(f"Updated year {year}, team {team_name}, games_played {game_played} with opponent {last_opponent}")

    conn.commit()

def main():
    # Update round_opp for each team and year
    for year in range(2023, 2023 + 1):
        cursor.execute("SELECT DISTINCT team FROM [dbo].[Soccer-Stats] WHERE year = ?", year)
        teams = [row[0] for row in cursor.fetchall()]
        for team in teams:
            team_id = None
            for base_name, base_id in team_base_urls.items():
                if base_name in team:
                    team_id = base_id
                    break

            if team_id:
                update_round_opp_from_gamelog(year, team, team_id)
                print(f"Updated round_opp for team {team} in year {year}")
            else:
                print(f"No URL found for team {team}. Skipping.")

if __name__ == "__main__":
    main()
    conn.close()
