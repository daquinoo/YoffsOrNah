import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLS;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team base URLs for MLS (team codes)
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

def parse_standings(soup, table_id):
    standings = []
    table = soup.find('table', {'id': table_id})
    if table:
        print(f"Parsing standings from table: {table_id}")
        for row in table.find('tbody').find_all('tr'):
            rank_cell = row.find('th', {'data-stat': 'rank'})
            if rank_cell and 'playoff' in rank_cell.get('class', []):
                team_name_cell = row.find('td', {'data-stat': 'team'})
                notes_cell = row.find('td', {'data-stat': 'notes'})
                if team_name_cell:
                    team_name = team_name_cell.text.strip()
                    had_bye = 'Conference Semifinals' in (notes_cell.text if notes_cell else '')
                    standings.append({'team_name': team_name, 'had_bye': had_bye})
    return standings

def parse_gamelog(soup):
    table = soup.find('table', {'id': 'matchlogs_for'})
    if not table:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if 'id="matchlogs_for"' in comment:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table', {'id': 'matchlogs_for'})
                if table:
                    break
    
    if not table:
        print("No match logs table found.")
        return []

    print("Parsing match logs table.")
    rows = table.find('tbody').find_all('tr')
    match_logs = []
    game_count = 0
    ignore_rounds = ["Regular Season", "Group Stage", "Round of 16", "Quarterfinals", "Semifinals", "Final"]
    for row in rows:
        if 'spacer' in row.get('class', []):
            continue  # Skip separator rows
        round_cell = row.find('td', {'data-stat': 'round'})
        if round_cell and round_cell.text.strip() not in ignore_rounds:
            game_count += 1
            match_round = round_cell.text.strip()
            match_logs.append({'games': game_count, 'round': match_round})
    return match_logs

def update_database(year, team_name, game_logs, had_bye):
    if not game_logs:
        return

    print(f"Updating database for team {team_name}, year {year} (Bye: {had_bye})")
    game_logs.sort(key=lambda x: x['games'], reverse=True)
    rounds = []
    current_round = game_logs[0]['round']
    current_series = []

    for log in game_logs:
        if log['round'] != current_round:
            rounds.insert(0, current_series)  # Prepend current_series to rounds
            current_series = []
            current_round = log['round']
        current_series.append(log)
    
    rounds.insert(0, current_series)  # Prepend the last current_series to rounds
    
    num_rounds = len(rounds)
    print(f"Number of playoff rounds: {num_rounds}")
    
    # Null all fields for games_played 1 through 5
    update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
    end_range = 7 if year == 2018 and had_bye == True else 6

    for games_played in range(1, end_range):
        for field in update_fields + (['yoffs_wc'] if year == 2023 else []):
            print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
            cursor.execute(f"""
                UPDATE [dbo].[Soccer-Stats]
                SET {field} = NULL
                WHERE year = ? AND team = ?
                AND games_played = ?
            """, (year, team_name, games_played))

    # Process remaining playoff rounds
    i = 0
    while i < num_rounds:
        for j in range(len(rounds[i])):
            games = rounds[i][j]['games']
            games_played = games + 5
            current_round = rounds[i][j]['round']
            print(f"Processing round: {current_round} for team {team_name}, year {year}, games_played {games_played}")

            if current_round == "Play-In Round":  # Handle Play-in Round
                print(f"Found Play-in round for team {team_name}, year {year}")
                update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
                for field in update_fields:
                    print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
                    cursor.execute(f"""
                        UPDATE [dbo].[Soccer-Stats]
                        SET {field} = NULL
                        WHERE year = ? AND team = ?
                        AND games_played = ?
                    """, (year, team_name, games_played))
                # Remove the play-in round after handling it
                rounds.pop(i)
                num_rounds -= 1
                break

            if year == 2023 and current_round == "Wild Card Round":  # Handle Wild Card Round
                print(f"Found Wild Card round for team {team_name}, year {year}")
                update_fields = ['yoffs_wc', 'yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
                for field in update_fields:
                    if field != 'yoffs_wc':
                        print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
                        cursor.execute(f"""
                            UPDATE [dbo].[Soccer-Stats]
                            SET {field} = NULL
                            WHERE year = ? AND team = ?
                            AND games_played = ?
                        """, (year, team_name, games_played))
                # Remove the wild card round after handling it
                rounds.pop(i)
                num_rounds -= 1
                break

            if j == 0:
                if len(rounds[i]) == 1:
                    if not had_bye and i == 0:  # First round of playoffs
                        update_fields = ['yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
                    elif (had_bye and i == 0) or (not had_bye and i == 1):  # Second round of playoffs
                        update_fields = ['yoffs_rdthr', 'yoffs_champ']
                    elif (had_bye and i == 1) or (not had_bye and i == 2):  # Third round of playoffs
                        update_fields = ['yoffs_champ']
                    elif (had_bye and i == 2) or (not had_bye and i == 3):  # Fourth round of playoffs (finals)
                        continue
                else:
                    print(f"Skipping update for highest games {games} in round {i + 1}")
                    continue  # Skip the highest value of games for the current round
            else:
                if not had_bye and i == 0:  # First round of playoffs
                    update_fields = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
                elif (had_bye and i == 0) or (not had_bye and i == 1):  # Second round of playoffs
                    update_fields = ['yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
                elif (had_bye and i == 1) or (not had_bye and i == 2):  # Third round of playoffs
                    update_fields = ['yoffs_rdthr', 'yoffs_champ']
                elif (had_bye and i == 2) or (not had_bye and i == 3):  # Fourth round of playoffs (finals)
                    update_fields = ['yoffs_champ']
            
            for field in update_fields:
                print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played}")
                cursor.execute(f"""
                    UPDATE [dbo].[Soccer-Stats]
                    SET {field} = NULL
                    WHERE year = ? AND team = ?
                    AND games_played = ?
                """, (year, team_name, games_played))

        # Only increment i if the current round is not play-in or wild card
        if current_round not in ["Play-In Round", "Wild Card Round"]:
            i += 1

    conn.commit()
    print(f"Database updated for team {team_name}, year {year}")

def main():
    for year in range(2018, 2023 + 1):
        print(f"Processing year {year}")
        url = f"https://fbref.com/en/comps/22/{year}/{year}-Major-League-Soccer-Stats"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        standings_tables = [
            f'results{year}221Eastern-Conference_overall', 
            f'results{year}221Western-Conference_overall'
        ]

        standings = []
        for table_id in standings_tables:
            standings += parse_standings(soup, table_id)

        for team_info in standings:
            team_name = team_info['team_name']
            had_bye = team_info['had_bye']
            team_code = next((code for name, code in team_base_urls.items() if name in team_name), None)
            if team_code:
                team_url = f"https://fbref.com/en/squads/{team_code}/{year}/matchlogs/all_comps/shooting/{team_name.replace(' ', '-')}-Match-Logs-All-Competitions"
                print(f"Fetching game logs for team: {team_name} from URL: {team_url}")
                html_content = fetch_html(team_url)
                team_soup = BeautifulSoup(html_content, 'html.parser')
                game_logs = parse_gamelog(team_soup)
                # Handle special cases for play-in round and wildcard round in 2023
                update_database(year, team_name, game_logs, had_bye)
        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
