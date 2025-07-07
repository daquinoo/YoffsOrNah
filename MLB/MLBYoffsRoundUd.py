import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLB;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

team_nicknames = [
    'Orioles', 'Rays', 'Blue Jays', 'Yankees', 'Red Sox', 'Twins', 'Tigers', 'Cleveland',
    'White Sox', 'Royals', 'Astros', 'Rangers', 'Mariners', 'Angels', 'Athletics', 'Braves',
    'Phillies', 'Marlins', 'Mets', 'Nationals', 'Brewers', 'Cubs', 'Reds', 'Pirates',
    'Cardinals', 'Dodgers', 'Diamondbacks', 'Padres', 'Giants', 'Rockies'
]

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
    round_col = {
        "World Series": "yoffs_champ",
        "ALWC": "yoffs_rdone", "NLWC": "yoffs_rdone",
        "ALDS": "yoffs_rdone" if year < 2012 else "yoffs_rtwo",
        "NLDS": "yoffs_rdone" if year < 2012 else "yoffs_rtwo",
        "ALCS": "yoffs_rtwo" if year < 2012 else "yoffs_rdthr",
        "NLCS": "yoffs_rtwo" if year < 2012 else "yoffs_rdthr"
    }

    for result in playoff_results:
        winner, loser, round_name = result
        round_column = round_col.get(round_name)
        
        cursor.execute(f"""
            UPDATE [dbo].[Baseball-Stats]
            SET {round_column} = 1
            WHERE year = ? AND team LIKE ?
        """, year, f"%{winner}%")
        
        cursor.execute(f"""
            UPDATE [dbo].[Baseball-Stats]
            SET {round_column} = 0
            WHERE year = ? AND team LIKE ?
        """, year, f"%{loser}%")
        
    conn.commit()

def extract_team_names_from_td(td):
    try:
        bold_team = None
        other_team = None
        for nickname in team_nicknames:
            if nickname in td.text:
                if td.find('strong') and nickname in td.find('strong').text:
                    bold_team = nickname
                else:
                    other_team = nickname
        return bold_team, other_team
    except Exception as e:
        print(f"Error extracting team names: {e}")
        return None, None

def determine_round(year, round_text):
    if "World Series" in round_text:
        return "World Series"
    if year >= 2012:
        if "ALWC" in round_text or "NLWC" in round_text:
            return "ALWC" if "ALWC" in round_text else "NLWC"
        if "ALDS" in round_text or "NLDS" in round_text:
            return "ALDS" if "ALDS" in round_text else "NLDS"
        if "ALCS" in round_text or "NLCS" in round_text:
            return "ALCS" if "ALCS" in round_text else "NLCS"
    else:
        if "ALDS" in round_text or "NLDS" in round_text:
            return "ALDS" if "ALDS" in round_text else "NLDS"
        if "ALCS" in round_text or "NLCS" in round_text:
            return "ALCS" if "ALCS" in round_text else "NLCS"
    return None

def fetch_playoff_results():
    url = f"https://www.baseball-reference.com/postseason/"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'id': 'postseason_series'})

    # Check if table is commented out
    if table is None:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        playoff_results_comment = next((comment for comment in comments if 'id="postseason_series"' in comment), None)
        if playoff_results_comment:
            table_soup = BeautifulSoup(playoff_results_comment, 'html.parser')
            table = table_soup.find('table', {'id': 'postseason_series'})

    if table is None:
        print(f"Error: 'postseason_series' table not found")
        return []

    playoff_results = []

    for row in table.find('tbody').find_all('tr'):
        # Skip rows that are headers
        if 'thead' in row.get('class', []):
            continue
        round_elem = row.find('th', {'class': 'left'})
        if round_elem:
            round_text = round_elem.text.strip()
            year_match = re.search(r'(\d{4})', round_text)
            if year_match:
                year = int(year_match.group(1))
                if year >= 2000:
                    round_name = determine_round(year, round_text)
                    if round_name:
                        cells = row.find_all('td', {'class': 'left'})
                        if cells and len(cells) > 0:
                            winner, loser = extract_team_names_from_td(cells[0])
                            if winner and loser:
                                playoff_results.append((year, winner, loser, round_name))
                            else:
                                print(f"Error: Could not extract teams from match_info: {cells[0].text.strip()}")

    return playoff_results

def main():
    playoff_results = fetch_playoff_results()
    for result in playoff_results:
        year, winner, loser, round_name = result
        update_playoff_results(year, [(winner, loser, round_name)])
        print(f"Finished updating year {year}")
    
    # Update playoff presence for teams with byes
    for year in range(2012, 2024):
        cursor.execute(f"""
            UPDATE [dbo].[Baseball-Stats]
            SET yoffs_rdone = 1
            WHERE year = ? AND yoffs_rdone IS NULL AND yoffs_rtwo IS NOT NULL
        """, year)
        conn.commit()
        print(f"Updated playoff presence for teams with byes in year {year}")

if __name__ == "__main__":
    main()
    conn.close()
