import requests
from bs4 import BeautifulSoup, Comment
import pyodbc

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};'
                      'Server=tcp:yoffsornah.database.windows.net,1433;'
                      'Database=YoffsOrNah-base-NFL;Uid=danny1phantom;'
                      'Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;'
                      'Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        print("Failed to retrieve the webpage")
        return None

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

def update_database(data, year):  # Assuming year is 2023 if not specified
    for entry in data:
        try:
            cursor.execute("""
                UPDATE [dbo].[Football-Stats]
                SET twopa_pg = CAST(? AS DECIMAL(10,3)), twopsucc_pg = CAST(? AS DECIMAL(10,3)),
                    sfty_pg = CAST(? AS DECIMAL(10,3)), def_TD_per_game = CAST(? AS DECIMAL(10,3))
                WHERE team = ? AND year = ?
            """, (entry['twopa_pg'], entry['twopsucc_pg'], entry['sfty_pg'], entry['def_TD_per_game'], entry['team_name'], year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data: {e}")

def main():
    url = "https://www.pro-football-reference.com/years/2023/#all_team_scoring"
    html_content = fetch_html(url)
    if html_content:
        offense_data = parse_offense_stats(html_content)
        if offense_data:
            update_database(offense_data, 2023)
            print("Offense data updated successfully.")
        else:
            print("No valid data parsed from the HTML.")
    conn.close()

if __name__ == "__main__":
    main()

