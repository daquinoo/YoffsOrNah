import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLB;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team base URLs
team_base_urls = {
    'Orioles': 'Orioles',
    'Tampa Bay Rays': 'Tampa Bay Rays',
    'Tampa Bay Devil Rays': 'Tampa Bay Devil Rays',
    'Blue Jays': 'Blue Jays',
    'Yankees': 'Yankees',
    'Red Sox': 'Red Sox',
    'Twins': 'Twins',
    'Tigers': 'Tigers',
    'Cleveland': 'Cleveland',
    'White Sox': 'White Sox',
    'Royals': 'Royals',
    'Astros': 'Astros',
    'Rangers': 'Rangers',
    'Mariners': 'Mariners',
    'Los Angeles Angels': 'Los Angeles Angels',
    'Anaheim Angels': 'Anaheim Angels',
    'Athletics': 'Athletics',
    'Braves': 'Braves',
    'Phillies': 'Phillies',
    'Miami Marlins': 'Miami Marlins',
    'Florida Marlins': 'Florida Marlins',
    'Mets': 'Mets',
    'Nationals': 'Nationals',
    'Montreal Expos': 'Montreal Expos',
    'Brewers': 'Brewers',
    'Cubs': 'Cubs',
    'Reds': 'Reds',
    'Pirates': 'Pirates',
    'Cardinals': 'Cardinals',
    'Dodgers': 'Dodgers',
    'Diamondbacks': 'Diamondbacks',
    'Padres': 'Padres',
    'Giants': 'Giants',
    'Rockies': 'Rockies'
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

def parse_postseason_table(soup):
    postseason_table = soup.find('table', {'id': 'postseason'})
    if not postseason_table:
        print("Postseason table not found directly in HTML, checking comments.")
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        postseason_comment = next((comment for comment in comments if 'id="postseason"' in comment), None)
        if postseason_comment:
            postseason_table = BeautifulSoup(postseason_comment, 'html.parser').find('table', {'id': 'postseason'})
            if postseason_table:
                print("Postseason table found in comments.")
            else:
                print("Postseason table not found in comments.")
        else:
            print("No comment containing postseason table found.")

    team_postseason_counts = {}
    team_round_appearances = {}

    if postseason_table:
        for row in postseason_table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 2:
                round_name = cells[0].text.strip()
                result = cells[2].text.strip()

                for team in team_base_urls:
                    if team in result:
                        if team not in team_postseason_counts:
                            team_postseason_counts[team] = 0
                            team_round_appearances[team] = set()
                        team_postseason_counts[team] += 1
                        team_round_appearances[team].add(round_name)

    return team_postseason_counts, team_round_appearances

def fetch_game_played_values(year, team_name):
    team_substr = team_base_urls.get(team_name)
    query = """
        SELECT DISTINCT games_played
        FROM [dbo].[Baseball-Stats]
        WHERE year = ? AND team LIKE ?
        ORDER BY games_played DESC
    """
    params = (year, '%' + team_substr + '%')
    cursor.execute(query, params)
    games_played_values = [row[0] for row in cursor.fetchall()]
    if games_played_values:
        print(f"Games played values for {team_name} in {year}: {games_played_values}")
    else:
        print(f"No games played values found for {team_name} in {year}. Query: {query}, Params: {params}")
    return games_played_values

def update_playoff_rounds(year, team_name, postseason_count, round_appearances, rounds, had_bye):
    num_rounds = postseason_count
    games_played_values = fetch_game_played_values(year, team_name)

    print(f"Updating playoff rounds for team {team_name}, year {year}, had_bye: {had_bye}, rounds: {rounds}, postseason_count: {postseason_count}, round_appearances: {round_appearances}")

    if not games_played_values:
        print(f"No game logs found for team {team_name} in year {year}. Skipping update.")
        return

    for idx, games_played_to_update in enumerate(games_played_values[1:]):
        if games_played_to_update is None:
            continue

        null_fields = []  # Initialize the variable to avoid referencing before assignment
        print(f"Processing idx: {idx}, games_played_to_update: {games_played_to_update}")

        if year < 2012:
            if num_rounds == 3:
                if idx == 0:
                    null_fields.append('yoffs_champ')
                elif idx == 1:
                    null_fields.extend(['yoffs_champ', 'yoffs_rtwo'])
                else:
                    null_fields.extend(['yoffs_champ', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_rounds == 2:
                if idx == 0:
                    null_fields.extend(['yoffs_champ', 'yoffs_rtwo'])
                else:
                    null_fields.extend(['yoffs_champ', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_rounds == 1:
                null_fields.extend(['yoffs_champ', 'yoffs_rtwo', 'yoffs_rdone'])
        else:
            if num_rounds == 4:
                if idx == 0:
                    null_fields.append('yoffs_champ')
                elif idx == 1:
                    null_fields.extend(['yoffs_champ', 'yoffs_rdthr'])
                elif idx == 2:
                    null_fields.extend(['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo'])
                else:
                    null_fields.extend(['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_rounds == 3:
                if not had_bye:
                    if idx == 0:
                        null_fields.append('yoffs_rdthr')
                    elif idx == 1:
                        null_fields.extend(['yoffs_rdthr', 'yoffs_rtwo'])
                    else:
                        null_fields.extend(['yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone'])
                else:
                    if idx == 0:
                        null_fields.append('yoffs_champ')
                    elif idx == 1:
                        null_fields.extend(['yoffs_champ', 'yoffs_rdthr'])
                    else:
                        null_fields.extend(['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_rounds == 2:
                if not had_bye:
                    if idx == 0:
                        null_fields.append('yoffs_rtwo')
                    else:
                        null_fields.extend(['yoffs_rtwo', 'yoffs_rdone'])
                else:
                    if idx == 0:
                        null_fields.append('yoffs_rdthr')
                    else:
                        null_fields.extend(['yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_rounds == 1:
                if not had_bye:
                    null_fields.append('yoffs_rdone')
                else:
                    null_fields.extend(['yoffs_rtwo', 'yoffs_rdone'])

        print(f"Null fields for idx {idx}: {null_fields}")

        for field in null_fields:
            print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played_to_update}")
            cursor.execute(f"""
                UPDATE [dbo].[Baseball-Stats]
                SET {field} = NULL
                WHERE year = ? AND team LIKE ? AND games_played = ?
            """, (year, '%' + team_base_urls.get(team_name) + '%', games_played_to_update))
            rows_affected = cursor.rowcount
            if rows_affected > 0:
                print(f"Successfully updated {field} for {team_name} in {year} with games_played {games_played_to_update}")
            else:
                print(f"No rows updated for {field} for {team_name} in {year} with games_played {games_played_to_update}")

    conn.commit()

def main():
    for year in range(2000, 2024):
        url = f"https://www.baseball-reference.com/leagues/majors/{year}-standings.shtml"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')

        team_postseason_counts, team_round_appearances = parse_postseason_table(soup)
        rounds = list(set(round for rounds in team_round_appearances.values() for round in rounds))
        print(f"Rounds found for {year}: {rounds}")

        for team_name, postseason_count in team_postseason_counts.items():
            round_appearances = team_round_appearances[team_name]
            had_bye = False
            if year >= 2012:
                had_bye = 'Wild Card Game' not in round_appearances and 'Wild Card Series' not in round_appearances
            print(f"Team: {team_name}, Had Bye: {had_bye}, Postseason Count: {postseason_count}, Round Appearances: {round_appearances}")
            update_playoff_rounds(year, team_name, postseason_count, round_appearances, rounds, had_bye)

        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
