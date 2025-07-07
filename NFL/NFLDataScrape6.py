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

def parse_stats(html_content, table_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    table_comment = next((comment for comment in comments if f'id="{table_id}"' in comment), None)

    if table_comment:
        table_soup = BeautifulSoup(table_comment, 'html.parser')
        tbody = table_soup.find('table', id=table_id).find('tbody')
        return tbody
    else:
        soup = BeautifulSoup(html_content, 'html.parser')
        tbody = soup.find('table', id=table_id).find('tbody')
        return tbody

def collect_team_data(html_content):
    data = {}
    stats = ['team_stats', 'returns', 'team_scoring', 'passing']
    for stat in stats:
        tbody = parse_stats(html_content, stat)
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if cols:
                    team_name = cols[0].text.strip()
                    if team_name not in data:
                        data[team_name] = {}

                    if stat == 'team_stats':
                        games_played = int(cols[1].text.strip())
                        data[team_name]['games_played'] = games_played
                        data[team_name].update({
                            'yds_all_pg': float(cols[3].text.strip()) / games_played,
                            'pts_all_pg': float(cols[2].text.strip()) / games_played,
                            'turnovers_frc_pg': float(cols[6].text.strip()) / games_played,
                            'pass_yds_all_pg': float(cols[11].text.strip()) / games_played,
                            'rush_yds_all_pg': float(cols[17].text.strip()) / games_played,
                            'pass_TD_all_pg': float(cols[12].text.strip()) / games_played,
                            'rush_TD_all_pg': float(cols[18].text.strip()) / games_played,
                            'opp_pen_pg': float(cols[21].text.strip()) / games_played,
                            'opp_penyds_pg': float(cols[22].text.strip()) / games_played
                        })

                    elif stat == 'returns':
                        punt_ret_yds = float(cols[3].text.strip())
                        kick_ret_yds = float(cols[7].text.strip())
                        punt_ret_td = float(cols[4].text.strip())
                        kick_ret_td = float(cols[8].text.strip())
                        data[team_name].update({
                            'ST_yds_all_pg': (punt_ret_yds + kick_ret_yds) / games_played,
                            'ST_TD_all_pg': (punt_ret_td + kick_ret_td) / games_played
                        })

                    elif stat == 'team_scoring':
                        safety = float(cols[17].text.strip()) if cols[17].text.strip().isdigit() else 0
                        intTDall_pg = float(cols[6].text.strip()) if cols[6].text.strip().isdigit() else 0
                        fumTDall_pg = float(cols[7].text.strip()) if cols[7].text.strip().isdigit() else 0
                        othTDall_pg = float(cols[8].text.strip()) if cols[8].text.strip().isdigit() else 0
                        defTDall_pg = (intTDall_pg + fumTDall_pg + othTDall_pg) / games_played
                        data[team_name].update({
                            'sfty_all_pg': safety / games_played,
                            'def_TD_all_pg': defTDall_pg
                        })

    return data

def update_database(data, year):
    for team_name, stats in data.items():
        try:
            cursor.execute("""
                UPDATE [dbo].[Football-Stats]
                SET yds_all_pg = ?, pts_all_pg = ?, def_TD_all_PG = ?, turnovers_frc_pg = ?,
                    pass_yds_all_pg = ?, rush_yds_all_pg = ?, pass_TD_all_pg = ?, rush_TD_all_pg = ?,
                    ST_yds_all_pg = ?, ST_TD_all_pg = ?, opp_pen_pg = ?, opp_penyds_pg = ?,
                    sfty_all_pg = ?
                WHERE team = ? AND year = ?
            """, (stats.get('yds_all_pg'), stats.get('pts_all_pg'), stats.get('def_TD_all_pg'),
                  stats.get('turnovers_frc_pg'), stats.get('pass_yds_all_pg'), stats.get('rush_yds_all_pg'),
                  stats.get('pass_TD_all_pg'), stats.get('rush_TD_all_pg'), stats.get('ST_yds_all_pg'),
                  stats.get('ST_TD_all_pg'), stats.get('opp_pen_pg'), stats.get('opp_penyds_pg'),
                  stats.get('sfty_all_pg'), team_name, year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data for {team_name}: {e}")


def main():
    url = "https://www.pro-football-reference.com/years/2023/opp.htm"
    html_content = fetch_html(url)
    if html_content:
        data = collect_team_data(html_content)
        if data:
            update_database(data, 2023)
            print("Database updated successfully.")
        else:
            print("No valid data parsed from the HTML.")
    else:
        print("Failed to fetch HTML content.")
    conn.close()

if __name__ == "__main__":
    main()


