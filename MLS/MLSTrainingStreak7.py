import requests
from bs4 import BeautifulSoup
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLS;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
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
    'Dynamo FC': '0d885416',
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

# Fetch HTML content with Scrapfly
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

# Parse standings to get playoff teams
def parse_standings(soup, table_id):
    standings = []
    table = soup.find('table', {'id': table_id})
    if table:
        for row in table.find('tbody').find_all('tr'):
            rank_cell = row.find('th', {'data-stat': 'rank'})
            if rank_cell and 'playoff' in rank_cell.get('class', []):
                team_name_cell = row.find('td', {'data-stat': 'team'})
                if team_name_cell:
                    team_name = team_name_cell.text.strip()
                    standings.append(team_name)
    return standings

# Extract numerical value from a cell, ignoring contents in <small>
def get_numeric_value(cell):
    if cell:
        small = cell.find('small')
        if small:
            small.extract()
        value = cell.text.strip()
        return value if value else '0'
    return '0'

# Parse team stats from each game log
def parse_misc_stats(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    table_id = "matchlogs_for"
    table = soup.find('table', {'id': table_id})
    game_logs = []

    if table:
        rows = table.find('tbody').find_all('tr')
        regular_season_games = [row for row in rows if row.find('td', {'data-stat': 'round'}) and row.find('td', {'data-stat': 'round'}).text == 'Regular Season']
        last_five_regular_season_games = regular_season_games[-5:] if len(regular_season_games) >= 5 else regular_season_games
        last_regular_season_game_index = rows.index(last_five_regular_season_games[-1])

        # Collect last 5 regular season games
        for row in last_five_regular_season_games:
            game_log = {
                'aerial_perc': get_numeric_value(row.find('td', {'data-stat': 'aerials_won_pct'})),
                'cross_pg': get_numeric_value(row.find('td', {'data-stat': 'crosses'})),
                'owng_conc_pg': get_numeric_value(row.find('td', {'data-stat': 'own_goals'})),
                'looseballs_rec_pg': get_numeric_value(row.find('td', {'data-stat': 'ball_recoveries'})),
                'pkwon_pg': get_numeric_value(row.find('td', {'data-stat': 'pens_won'})),
                'pkconc_pg': get_numeric_value(row.find('td', {'data-stat': 'pens_conceded'})),
                'fls_pg': get_numeric_value(row.find('td', {'data-stat': 'fouls'})),
                'fld_pg': get_numeric_value(row.find('td', {'data-stat': 'fouled'}))
            }
            game_logs.append(game_log)

        # Collect all games after the last regular season game, handling spacer rows
        start_collecting = False
        for row in rows[last_regular_season_game_index:]:
            if row.get('class') and 'spacer' in row.get('class'):
                start_collecting = True
                continue

            if start_collecting:
                aerial_perc_cell = row.find('td', {'data-stat': 'aerials_won_pct'})
                cross_pg_cell = row.find('td', {'data-stat': 'crosses'})
                owng_conc_pg_cell = row.find('td', {'data-stat': 'own_goals'})
                looseballs_rec_pg_cell = row.find('td', {'data-stat': 'ball_recoveries'})
                pkwon_pg_cell = row.find('td', {'data-stat': 'pens_won'})
                pkconc_pg_cell = row.find('td', {'data-stat': 'pens_conceded'})
                fls_pg_cell = row.find('td', {'data-stat': 'fouls'})
                fld_pg_cell = row.find('td', {'data-stat': 'fouled'})
                if (aerial_perc_cell and cross_pg_cell and owng_conc_pg_cell and looseballs_rec_pg_cell and 
                    pkwon_pg_cell and pkconc_pg_cell and fls_pg_cell and fld_pg_cell):
                    game_log = {
                        'aerial_perc': get_numeric_value(aerial_perc_cell),
                        'cross_pg': get_numeric_value(cross_pg_cell),
                        'owng_conc_pg': get_numeric_value(owng_conc_pg_cell),
                        'looseballs_rec_pg': get_numeric_value(looseballs_rec_pg_cell),
                        'pkwon_pg': get_numeric_value(pkwon_pg_cell),
                        'pkconc_pg': get_numeric_value(pkconc_pg_cell),
                        'fls_pg': get_numeric_value(fls_pg_cell),
                        'fld_pg': get_numeric_value(fld_pg_cell)
                    }
                    game_logs.append(game_log)
    return game_logs

# Update game logs in the database
def update_game_logs(year, team_name, game_logs):
    for i, game_log in enumerate(game_logs):
        cursor.execute("""
            UPDATE [dbo].[Soccer-Stats]
            SET aerial_perc = ?, cross_pg = ?, owng_conc_pg = ?, looseballs_rec_pg = ?, 
                pkwon_pg = ?, pkconc_pg = ?, fls_pg = ?, fld_pg = ?
            WHERE year = ? AND team = ? AND games_played = ?
        """, (
            float(game_log['aerial_perc']), 
            float(game_log['cross_pg']), 
            float(game_log['owng_conc_pg']), 
            float(game_log['looseballs_rec_pg']), 
            float(game_log['pkwon_pg']), 
            float(game_log['pkconc_pg']), 
            float(game_log['fls_pg']), 
            float(game_log['fld_pg']), 
            year, team_name, i + 1
        ))
    conn.commit()

def main():
    years = range(2023, 2023+1)
    for year in years:
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
        
        for team_name in standings:
            team_code = next((code for name, code in team_base_urls.items() if name in team_name), None)
            if team_code:
                misc_url = f"https://fbref.com/en/squads/{team_code}/{year}/matchlogs/c22/misc/{team_name.replace(' ', '-')}-Match-Logs-Major-League-Soccer"
                misc_html_content = fetch_html(misc_url)
                misc_stats = parse_misc_stats(misc_html_content)
                update_game_logs(year, team_name, misc_stats)
            print(f"Finished updating {team_name}")

        print(f"Finished updating year {year}")

if __name__ == "__main__":
    main()
    conn.close()
