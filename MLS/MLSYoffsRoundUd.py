import requests
from bs4 import BeautifulSoup
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
try:
    conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLS;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
    cursor = conn.cursor()
except pyodbc.Error as e:
    print(f"Database connection error: {e}")
    raise

team_nicknames = [
    'FC Cincinnati', 'Orlando City', 'D.C. United', 'Crew', 'Philadelphia', 'NE Revolution',
    'Atlanta Utd', 'Nashville', 'NY Red Bulls', 'Charlotte', 'CF Mon', 'NYCFC', 'Fire', 'Inter Miami',
    'Toronto FC', 'St. Louis', 'Seattle', 'LAFC', 'Dynamo', 'RSL', 'Vancouver', 'FC Dallas',
    'Sporting KC', 'SJ Earthquakes', 'Portland Timbers', 'Minnesota Utd', 'Austin', 'LA Galaxy',
    'Rapids', 'Montreal'
]

round_col = {
    "Knockout round": "yoffs_rdone", "First Round": "yoffs_rdone", "Round 1": "yoffs_rdone",
    "Wild Card Round": "yoffs_wc",  # 2023 only
    "Conference Semifinals": "yoffs_rtwo",
    "Conference Finals": "yoffs_rdthr",
    "MLS Cup": "yoffs_champ"
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

def update_playoff_results(year, playoff_results):
    try:
        for result in playoff_results:
            round_name, winner, loser = result
            round_column = round_col.get(round_name)
            
            if round_column:
                print(f"Updating {winner} for round {round_name} with 1")
                cursor.execute(f"""
                    UPDATE [dbo].[Soccer-Stats]
                    SET {round_column} = 1
                    WHERE year = ? AND team LIKE ?
                """, year, f"%{winner}%")
                
                print(f"Updating {loser} for round {round_name} with 0")
                cursor.execute(f"""
                    UPDATE [dbo].[Soccer-Stats]
                    SET {round_column} = 0
                    WHERE year = ? AND team LIKE ?
                """, year, f"%{loser}%")
            
        conn.commit()
    except pyodbc.Error as e:
        print(f"Database update error: {e}")
        raise

def fetch_playoff_results(year):
    url = f"https://fbref.com/en/comps/22/{year}/{year}-Major-League-Soccer-Stats"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    playoff_section = soup.find('span', {'data-label': 'MLS Cup Playoffs'}).find_parent('div')

    playoff_results = []
    
    current_round = None
    for h3 in playoff_section.find_all_next('h3'):
        round_name = h3.text.strip()
        print(f"Detected round: {round_name}")
        current_round = determine_round(round_name)
        
        if current_round:
            matchup_divs = h3.find_next_sibling('div', class_='matchup')
            if matchup_divs:
                print(f"Processing matchups for round: {current_round}")
                for match_summary in matchup_divs.find_all('div', class_='match-summary'):
                    team1_div = None
                    team2_div = None
                    winner_div = None
                    loser_div = None
                    
                    # Find divs with class names
                    for div in match_summary.find_all('div', recursive=False):
                        class_name = div.get('class')
                        if class_name:
                            if 'matchup-team' in class_name:
                                if 'team1' in class_name:
                                    team1_div = div
                                if 'team2' in class_name:
                                    team2_div = div
                                if 'winner' in class_name:
                                    winner_div = div

                    # Determine loser div
                    loser_div = team2_div if winner_div == team1_div else team1_div

                    # Print div contents for diagnosis
                    print(f"team1_div: {team1_div}")
                    print(f"team2_div: {team2_div}")
                    print(f"winner_div: {winner_div}")
                    print(f"loser_div: {loser_div}")

                    if winner_div and loser_div:
                        winner = extract_team_nickname(winner_div)
                        loser = extract_team_nickname(loser_div)
                        if winner and loser:
                            print(f"Found matchup: {winner} (winner) vs {loser} (loser) in round {current_round}")
                            playoff_results.append((current_round, winner, loser))
                    else:
                        print(f"Warning: No winner found in {match_summary}")
            
            # Special handling for Round One in 2023
            if year == 2023 and current_round == "Wild Card Round":
                round_one_section = soup.find('div', {'class': 'section_heading', 'id': 'Round One_sh'})
                if round_one_section:
                    print("Processing matchups for Round One in 2023")
                    round_one_content = round_one_section.find_next_sibling('div', {'class': 'section_content', 'id': 'div_Round One'})
                    if round_one_content:
                        for table in round_one_content.find_all('table'):
                            winner_row = table.find('tr', class_='bold hilite')
                            loser_row = winner_row.find_next_sibling('tr') if winner_row else None
                            winner_team = extract_team_nickname_from_table(winner_row)
                            loser_team = extract_team_nickname_from_table(loser_row)
                            if winner_team and loser_team:
                                print(f"Found matchup: {winner_team} (winner) vs {loser_team} (loser) in round Knockout round")
                                playoff_results.append(("Knockout round", winner_team, loser_team))
                            else:
                                print(f"Warning: Could not determine teams from table: {table}")

    return playoff_results

def extract_team_nickname(div):
    try:
        team_name = div.find('a').text.strip()
        for nickname in team_nicknames:
            if nickname in team_name:
                return nickname
    except Exception as e:
        print(f"Error extracting team name: {e}")
    return None

def extract_team_nickname_from_table(row):
    try:
        team_name_td = row.find('td', {'data-stat': 'team'})
        if team_name_td:
            team_name = team_name_td.text.strip()
            for nickname in team_nicknames:
                if nickname in team_name:
                    return nickname
    except Exception as e:
        print(f"Error extracting team name from table: {e}")
    return None

def determine_round(h3_text):
    if "Knockout round" in h3_text or "First Round" in h3_text or "Round 1" in h3_text:
        return "Knockout round"
    if "Wild Card Round" in h3_text:
        return "Wild Card Round"
    if "Conference Semifinals" in h3_text:
        return "Conference Semifinals"
    if "Conference Finals" in h3_text:
        return "Conference Finals"
    if "MLS Cup" in h3_text:
        return "MLS Cup"
    return None

def set_bye_teams(year):
    try:
        cursor.execute(f"""
            UPDATE [dbo].[Soccer-Stats]
            SET yoffs_rdone = 1
            WHERE year = ? AND yoffs_rtwo IS NOT NULL AND yoffs_rdone IS NULL
        """, year)
        conn.commit()
    except pyodbc.Error as e:
        print(f"Database bye update error: {e}")
        raise

def main():
    try:
        for year in range(2023, 2023+1):
            print(f"Processing year {year}...")
            playoff_results = fetch_playoff_results(year)
            if playoff_results:
                print(f"Updating database for year {year} with {len(playoff_results)} results...")
                update_playoff_results(year, playoff_results)
                set_bye_teams(year)
                print(f"Finished updating year {year}")
    except Exception as e:
        print(f"An error occurred during processing: {e}")
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()
