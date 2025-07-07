
import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};'
                      'Server=tcp:yoffsornah.database.windows.net,1433;'
                      'Database=YoffsOrNah-train-NFL;Uid=danny1phantom;'
                      'Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;'
                      'Connection Timeout=30;')
cursor = conn.cursor()

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

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

def parse_offense_stats(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    offense_comment = next((comment for comment in comments if 'id="team_scoring"' in comment), None)
    
    if offense_comment:
        offense_soup = BeautifulSoup(offense_comment, 'html.parser')
        tbody = offense_soup.find('table', id='team_scoring').find('tbody')
    else:
        print("Failed to find the 'Scoring Offense' table within the HTML comments.")
        return []
    
    rows = tbody.find_all('tr') if tbody else []
    data = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) > 18:  # Ensures enough columns to parse the needed data
            team_name = cols[0].text.strip()
            games_played = int(cols[1].text.strip())
            
            intTD_pg = float(cols[6].text.strip()) if cols[6].text.strip().isdigit() else 0
            fumTD_pg = float(cols[7].text.strip()) if cols[7].text.strip().isdigit() else 0
            othTD_pg = float(cols[8].text.strip()) if cols[8].text.strip().isdigit() else 0
            defTD_pg = (intTD_pg + fumTD_pg + othTD_pg) / games_played
            
            two_pt_att = float(cols[11].text.strip()) if cols[11].text.strip().isdigit() else 0
            two_pt_md = float(cols[10].text.strip()) if cols[10].text.strip().isdigit() else 0
            twopsucc_pg = (two_pt_md / two_pt_att if two_pt_att != 0 else 0)
            twopa_pg = two_pt_att / games_played
            
            sfty = float(cols[17].text.strip()) if cols[17].text.strip().isdigit() else 0
            sfty_pg = sfty / games_played

            data.append({
                'team_name': team_name,
                'twopa_pg': twopa_pg,
                'twopsucc_pg': twopsucc_pg,
                'sfty_pg': sfty_pg,
                'def_TD_per_game': defTD_pg
            })

    return data

def update_database(data, year):
    for entry in data:
        try:
            cursor.execute("""
                UPDATE [dbo].[Football-Training-Stats]
                SET twopa_pg = CAST(? AS DECIMAL(10,3)), twopsucc_pg = CAST(? AS DECIMAL(10,3)),
                    sfty_pg = CAST(? AS DECIMAL(10,3)), def_TD_per_game = CAST(? AS DECIMAL(10,3))
                WHERE team = ? AND year = ?
            """, (entry['twopa_pg'], entry['twopsucc_pg'], entry['sfty_pg'], entry['def_TD_per_game'], entry['team_name'], year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data: {e}")

def main():
    for year in range(2023, 2023+1):
        url = f"https://www.pro-football-reference.com/years/{year}/#all_team_scoring"
        try:
            html_content = fetch_html(url)
            if html_content:
                offense_data = parse_offense_stats(html_content)
                if offense_data:
                    update_database(offense_data, year)
                    print(f"Offense data updated successfully for the year {year}.")
                else:
                    print(f"No valid data parsed from the HTML for the year {year}.")
            else:
                print(f"Failed to retrieve content for the year {year}.")
        except Exception as e:
            print(e)
    conn.close()

if __name__ == "__main__":
    main()
