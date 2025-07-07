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

def parse_team_stats(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    team_stats_comment = next((comment for comment in comments if 'id="team_stats"' in comment), None)
    if team_stats_comment:
        team_stats_soup = BeautifulSoup(team_stats_comment, 'html.parser')
        tbody = team_stats_soup.find('table', id='team_stats').find('tbody')
    else:
        print("Failed to find the table within the HTML comments.")
        return []

    rows = tbody.find_all('tr') if tbody else []
    data = []

    for row in rows:
        cols = row.find_all('td')
        if cols and len(cols) >= 24:  # Check if there are enough columns
            team_name = cols[0].text.strip()  # Correcting the index for team name
            games_played = int(cols[1].text.strip())  # Games played
            pts = float(cols[2].text.strip())  # Points
            yds = float(cols[3].text.strip())  # Yards
            turnovers = float(cols[6].text.strip())  # Turnovers
            pass_yds = float(cols[10].text.strip())  # Correcting the index for passing yards
            pass_td = float(cols[11].text.strip())  # Correcting the index for passing TDs
            rush_yds = float(cols[16].text.strip())  # Correcting the index for rushing yards
            rush_td = float(cols[17].text.strip())  # Correcting the index for rushing TDs
            penalties = float(cols[20].text.strip())  # Correcting the index for penalties
            pen_yds = float(cols[21].text.strip())  # Correcting the index for penalty yards

            games_played = max(games_played, 1)  # Avoid division by zero
            data.append({
                'team_name': team_name,
                'games_played': games_played,
                'pts_pg': pts/games_played,
                'yds_p_game': yds/games_played,
                'turnovers_pg': turnovers/games_played,
                'pass_ypg': pass_yds/games_played,
                'pass_TD_pg': pass_td/games_played,
                'rush_ypg': rush_yds/games_played,
                'rush_TD_pg': rush_td/games_played,
                'pen_pg': penalties/games_played,
                'penyds_ag': pen_yds/games_played
            })

    return data


import requests
from bs4 import BeautifulSoup, Comment
import pyodbc

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};'
                      'Server=tcp:yoffsornah.database.windows.net,1433;'
                      'Database=YoffsOrNah-base-NFL;Uid=danny1phantom;'
                      'Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;'
                      'Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        print("Failed to retrieve the webpage")
        return None

def parse_team_stats(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    team_stats_comment = next((comment for comment in comments if 'id="team_stats"' in comment), None)
    if team_stats_comment:
        team_stats_soup = BeautifulSoup(team_stats_comment, 'html.parser')
        tbody = team_stats_soup.find('table', id='team_stats').find('tbody')
    else:
        print("Failed to find the table within the HTML comments.")
        return []

    rows = tbody.find_all('tr') if tbody else []
    data = []

    for row in rows:
        cols = row.find_all('td')
        if cols and len(cols) >= 24:  # Check if there are enough columns
            team_name = cols[0].text.strip()  # Correcting the index for team name
            games_played = int(cols[1].text.strip())  # Games played
            pts = float(cols[2].text.strip())  # Points
            yds = float(cols[3].text.strip())  # Yards
            turnovers = float(cols[6].text.strip())  # Turnovers
            pass_yds = float(cols[11].text.strip())  # Correcting the index for passing yards
            pass_td = float(cols[12].text.strip())  # Correcting the index for passing TDs
            rush_yds = float(cols[17].text.strip())  # Correcting the index for rushing yards
            rush_td = float(cols[18].text.strip())  # Correcting the index for rushing TDs
            penalties = float(cols[21].text.strip())  # Correcting the index for penalties
            pen_yds = float(cols[22].text.strip())  # Correcting the index for penalty yards

            games_played = max(games_played, 1)  # Avoid division by zero
            data.append({
                'team_name': team_name,
                'games_played': games_played,
                'pts_pg': pts/games_played,
                'yds_p_game': yds/games_played,
                'turnovers_pg': turnovers/games_played,
                'pass_ypg': pass_yds/games_played,
                'pass_TD_pg': pass_td/games_played,
                'rush_ypg': rush_yds/games_played,
                'rush_TD_pg': rush_td/games_played,
                'pen_pg': penalties/games_played,
                'penyds_pg': pen_yds/games_played
            })

    return data

def update_database(data, year):  # Assuming year is 2023 if not specified
    for entry in data:
        try:
            cursor.execute("""
                UPDATE [dbo].[Football-Stats]
                SET games_played = ?, pts_pg = CAST(? AS DECIMAL(10,3)), yds_p_game = CAST(? AS DECIMAL(10,3)),
                    turnovers_pg = CAST(? AS DECIMAL(10,3)), pass_ypg = CAST(? AS DECIMAL(10,3)),
                    pass_TD_pg = CAST(? AS DECIMAL(10,3)), rush_ypg = CAST(? AS DECIMAL(10,3)),
                    rush_TD_pg = CAST(? AS DECIMAL(10,3)), pen_pg = CAST(? AS DECIMAL(10,3)),
                    penyds_pg = CAST(? AS DECIMAL(10,3))
                WHERE team = ? AND year = ?
            """, (entry['games_played'], entry['pts_pg'], entry['yds_p_game'],
                  entry['turnovers_pg'], entry['pass_ypg'], entry['pass_TD_pg'],
                  entry['rush_ypg'], entry['rush_TD_pg'], entry['pen_pg'], entry['penyds_pg'],
                  entry['team_name'], year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data: {e}")

def main():
    url = "https://www.pro-football-reference.com/years/2023/#all_team_stats"
    html_content = fetch_html(url)
    if html_content:
        data = parse_team_stats(html_content)
        if data:
            update_database(data, 2023)  # This line changes to call the update function
        else:
            print("No valid data parsed from the HTML.")
    conn.close()

if __name__ == "__main__":
    main()

