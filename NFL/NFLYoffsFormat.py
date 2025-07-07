import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampNFL;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team base URLs (the year will be dynamically inserted)
team_base_urls = {
    'Bills': 'https://www.pro-football-reference.com/teams/buf/{year}/gamelog/',
    'Dolphins': 'https://www.pro-football-reference.com/teams/mia/{year}/gamelog/',
    'Jets': 'https://www.pro-football-reference.com/teams/nyj/{year}/gamelog/',
    'Patriots': 'https://www.pro-football-reference.com/teams/nwe/{year}/gamelog/',
    'Ravens': 'https://www.pro-football-reference.com/teams/rav/{year}/gamelog/',
    'Browns': 'https://www.pro-football-reference.com/teams/cle/{year}/gamelog/',
    'Steelers': 'https://www.pro-football-reference.com/teams/pit/{year}/gamelog/',
    'Bengals': 'https://www.pro-football-reference.com/teams/cin/{year}/gamelog/',
    'Texans': 'https://www.pro-football-reference.com/teams/htx/{year}/gamelog/',
    'Jaguars': 'https://www.pro-football-reference.com/teams/jax/{year}/gamelog/',
    'Colts': 'https://www.pro-football-reference.com/teams/clt/{year}/gamelog/',
    'Titans': 'https://www.pro-football-reference.com/teams/oti/{year}/gamelog/',
    'Chiefs': 'https://www.pro-football-reference.com/teams/kan/{year}/gamelog/',
    'Raiders': 'https://www.pro-football-reference.com/teams/rai/{year}/gamelog/',
    'Broncos': 'https://www.pro-football-reference.com/teams/den/{year}/gamelog/',
    'Chargers': 'https://www.pro-football-reference.com/teams/sdg/{year}/gamelog/',
    'Cowboys': 'https://www.pro-football-reference.com/teams/dal/{year}/gamelog/',
    'Eagles': 'https://www.pro-football-reference.com/teams/phi/{year}/gamelog/',
    'Giants': 'https://www.pro-football-reference.com/teams/nyg/{year}/gamelog/',
    'Washington': 'https://www.pro-football-reference.com/teams/was/{year}/gamelog/',
    'Lions': 'https://www.pro-football-reference.com/teams/det/{year}/gamelog/',
    'Packers': 'https://www.pro-football-reference.com/teams/gnb/{year}/gamelog/',
    'Vikings': 'https://www.pro-football-reference.com/teams/min/{year}/gamelog/',
    'Bears': 'https://www.pro-football-reference.com/teams/chi/{year}/gamelog/',
    'Buccaneers': 'https://www.pro-football-reference.com/teams/tam/{year}/gamelog/',
    'Saints': 'https://www.pro-football-reference.com/teams/nor/{year}/gamelog/',
    'Falcons': 'https://www.pro-football-reference.com/teams/atl/{year}/gamelog/',
    'Panthers': 'https://www.pro-football-reference.com/teams/car/{year}/gamelog/',
    '49ers': 'https://www.pro-football-reference.com/teams/sfo/{year}/gamelog/',
    'Rams': 'https://www.pro-football-reference.com/teams/ram/{year}/gamelog/',
    'Seahawks': 'https://www.pro-football-reference.com/teams/sea/{year}/gamelog/',
    'Cardinals': 'https://www.pro-football-reference.com/teams/crd/{year}/gamelog/'
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

def parse_results(soup):
    teams_with_byes = set()
    wildcard_teams = set()
    division_teams = set()

    # Fetch the playoff results table from the comments
    table = soup.find('table', {'id': 'playoff_results'})
    if table:
        print("Playoff results table found directly in the HTML.")
    else:
        print("Playoff results table not found directly in the HTML. Checking comments.")
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        playoff_results_comment = next((comment for comment in comments if 'id="playoff_results"' in comment), None)
        if playoff_results_comment:
            print("Found playoff_results table in comments.")
            table_soup = BeautifulSoup(playoff_results_comment, 'html.parser')
            table = table_soup.find('table', {'id': 'playoff_results'})
            if table:
                print("Playoff results table successfully parsed from comment.")
        else:
            print("No comment containing playoff_results table found.")
            return teams_with_byes

    if table:
        # Extract team names from the WildCard and Division rows
        for row in table.find_all('tr'):
            week_num_cell = row.find('th', {'data-stat': 'week_num'})
            if week_num_cell:
                week_num = week_num_cell.text.strip()
                print(f"Processing row with week_num: {week_num}")
                winner_cell = row.find('td', {'data-stat': 'winner'})
                loser_cell = row.find('td', {'data-stat': 'loser'})

                winner_team = None
                loser_team = None

                if winner_cell:
                    if winner_cell.find('a'):
                        winner_team = winner_cell.find('a').text.strip()
                    else:
                        winner_team = winner_cell.text.strip()
                    print(f"Winner team: {winner_team}")

                if loser_cell:
                    if loser_cell.find('a'):
                        loser_team = loser_cell.find('a').text.strip()
                    else:
                        loser_team = loser_cell.text.strip()
                    print(f"Loser team: {loser_team}")

                if week_num == "WildCard":
                    if winner_team:
                        wildcard_teams.add(winner_team)
                    if loser_team:
                        wildcard_teams.add(loser_team)
                elif week_num == "Division":
                    if winner_team:
                        division_teams.add(winner_team)
                    if loser_team:
                        division_teams.add(loser_team)

        # Teams in the Division round but not in the WildCard round have a bye
        teams_with_byes = division_teams - wildcard_teams

        print(f"Wildcard teams: {wildcard_teams}")
        print(f"Division teams: {division_teams}")
        print(f"Teams with byes: {teams_with_byes}")

    return teams_with_byes


def parse_standings(soup, teams_with_byes):
    standings = []

    # Parse the main standings table
    for row in soup.find_all('tr'):
        if 'onecell' in row.get('class', []):
            continue
        if row.find('th', {'scope': 'row'}):
            team_name_cell = row.find('th', {'scope': 'row'})
            team_name = team_name_cell.text.strip()
            if '*' in team_name or '+' in team_name:
                team_name_cleaned = team_name.replace('*', '').replace('+', '').strip()
                had_bye = team_name_cleaned in teams_with_byes
                standings.append((team_name_cleaned, had_bye))
                print(f"Team: {team_name_cleaned}, Had bye: {had_bye}")
    return standings



def fetch_team_game_logs(team_name, url, year):
    print(f"Fetching game logs for team {team_name}, year {year}")
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    game_logs = []
    
    table = soup.find('table', {'id': f'playoff_gamelog{year}'})
    if table is None:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        tablecom = next((comment for comment in comments if f'id="playoff_gamelog"{year}' in comment), None)
        if tablecom:
            table_soup = BeautifulSoup(tablecom, 'html.parser')
            table = table_soup.find('table', {'id': f'playoff_gamelog{year}'})
    if table:
        rows = table.find('tbody').find_all('tr')
        current_week_num = None
        games_played = 0

        for row in rows[::-1]:  # iterate backwards
            week_num_cell = row.find('th', {'data-stat': 'week_num'})
            if week_num_cell and week_num_cell.text:
                week_num = week_num_cell.text.strip()
                if week_num != current_week_num:
                    games_played += 1
                    current_week_num = week_num
                game_log = {'games_played': games_played}
                game_logs.append(game_log)
    
    print(f"Game logs for team {team_name}, year {year}: {game_logs}")
    return game_logs

def update_playoff_rounds(year, team_name, game_logs, had_bye):
    num_games = len(game_logs)
    
    print(f"Updating playoff rounds for team {team_name}, year {year}, had_bye: {had_bye}, num_games: {num_games}")
    # Sort game_logs by games_played in decreasing order (if not already sorted)
    game_logs = sorted(game_logs, key=lambda x: x['games_played'], reverse=True)
    
    for idx, game_log in enumerate(game_logs):
        games_played = game_log['games_played']
        games_played_to_update = (games_played + 5) - (idx - (idx - 1))  # Keep the original calculation

        cursor.execute("""
            SELECT yoffs_rdone, yoffs_rtwo, yoffs_rdthr, yoffs_champ
            FROM [dbo].[Football-Stats]
            WHERE year = ? AND team = ? AND games_played = ?
        """, (year, team_name, games_played_to_update))
        row = cursor.fetchone()

        if row:
            yoffs_rdone, yoffs_rtwo, yoffs_rdthr, yoffs_champ = row
            print(f"Before update for team {team_name}, year {year}, games_played {games_played_to_update}:")
            print(f"yoffs_rdone: {yoffs_rdone}, yoffs_rtwo: {yoffs_rtwo}, yoffs_rdthr: {yoffs_rdthr}, yoffs_champ: {yoffs_champ}")
            
            update_fields = []
            if num_games == 4:
                if idx == 0:
                    update_fields.append('yoffs_champ')
                elif idx == 1:
                    update_fields.extend(['yoffs_champ', 'yoffs_rdthr'])
                elif idx == 2:
                    update_fields.extend(['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo'])
                elif idx >= 3:
                    update_fields.extend(['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_games == 3 and not had_bye:
                if idx == 0:
                    update_fields.append('yoffs_rdthr')
                elif idx == 1:
                    update_fields.extend(['yoffs_rdthr', 'yoffs_rtwo'])
                elif idx >= 2:
                    update_fields.extend(['yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_games == 3 and had_bye:
                if idx == 0:
                    update_fields.append('yoffs_champ')
                elif idx == 1:
                    update_fields.extend(['yoffs_champ', 'yoffs_rdthr'])
                elif idx >= 2:
                    update_fields.extend(['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_games == 2 and not had_bye:
                if idx == 0:
                    update_fields.append('yoffs_rtwo')
                elif idx >= 1:
                    update_fields.extend(['yoffs_rtwo', 'yoffs_rdone'])
            elif num_games == 2 and had_bye:
                if idx == 0:
                    update_fields.append('yoffs_rdthr')
                elif idx >= 1:
                    update_fields.extend(['yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone'])
            elif num_games == 1 and not had_bye:
                if idx >= 0:
                    update_fields.append('yoffs_rdone')
            elif num_games == 1 and had_bye:
                if idx >= 0:
                    update_fields.extend(['yoffs_rtwo', 'yoffs_rdone'])

            # Execute individual SET statements for each field
            for field in update_fields:
                print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played_to_update}")
                cursor.execute(f"""
                    UPDATE [dbo].[Football-Stats]
                    SET {field} = NULL
                    WHERE year = ? AND team = ? AND games_played = ?
                """, (year, team_name, games_played_to_update))

            # Re-fetch and print the row after update
            cursor.execute("""
                SELECT yoffs_rdone, yoffs_rtwo, yoffs_rdthr, yoffs_champ
                FROM [dbo].[Football-Stats]
                WHERE year = ? AND team = ? AND games_played = ?
            """, (year, team_name, games_played_to_update))
            row = cursor.fetchone()
            if row:
                yoffs_rdone, yoffs_rtwo, yoffs_rdthr, yoffs_champ = row
                print(f"After update for team {team_name}, year {year}, games_played {games_played_to_update}:")
                print(f"yoffs_rdone: {yoffs_rdone}, yoffs_rtwo: {yoffs_rtwo}, yoffs_rdthr: {yoffs_rdthr}, yoffs_champ: {yoffs_champ}")
                
    # Update the remaining rows where games_played_to_update > num_games
    for games_played_to_update in range(1, 6):
        update_fields = ['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone']
        for field in update_fields:
            print(f"Updating {field} to NULL for team {team_name}, year {year}, games_played {games_played_to_update}")
            cursor.execute(f"""
                UPDATE [dbo].[Football-Stats]
                SET {field} = NULL
                WHERE year = ? AND team = ? AND games_played = ?
            """, (year, team_name, games_played_to_update))

    conn.commit()


def main():
    for year in range(2021, 2024):
        url = f"https://www.pro-football-reference.com/years/{year}/#all_team_stats"
        html_content = fetch_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Fetch and parse playoff results
        teams_with_byes = parse_results(soup)
        
        afc_soup = soup.find('table', {'id': 'AFC'})
        nfc_soup = soup.find('table', {'id': 'NFC'})
        
        if afc_soup and nfc_soup:
            afc_data = parse_standings(afc_soup, teams_with_byes)
            nfc_data = parse_standings(nfc_soup, teams_with_byes)
            standings = afc_data + nfc_data
            for team_name, had_bye in standings:
                for key in team_base_urls:
                    if key in team_name:
                        team_url = team_base_urls[key].format(year=year)
                        game_logs = fetch_team_game_logs(team_name, team_url, year)
                        update_playoff_rounds(year, team_name, game_logs, had_bye)
                        break  # Once a match is found, no need to check further
        else:
            print(f"Error: Could not find AFC or NFC tables in the HTML for year {year}.")
        
        # Debug line to indicate the completion of the year
        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
