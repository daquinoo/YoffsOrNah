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

def parse_returns_stats(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    returns_comment = next((comment for comment in comments if 'id="returns"' in comment), None)
    
    if returns_comment:
        returns_soup = BeautifulSoup(returns_comment, 'html.parser')
        tbody = returns_soup.find('table', id='returns').find('tbody')
    else:
        print("Failed to find the returns table within the HTML comments.")
        return []

    rows = tbody.find_all('tr') if tbody else []
    data = []

    for row in rows:
        cols = row.find_all('td')
        if cols and len(cols) >= 12:  # Ensure there are enough columns
            team_name = cols[0].text.strip()
            games_played = int(cols[1].text.strip())
            punt_ret_yds = float(cols[3].text.strip())  # Punt Return Yards
            punt_ret_td = float(cols[4].text.strip())   # Punt Return TDs
            kick_ret_yds = float(cols[8].text.strip())  # Kick Return Yards
            kick_ret_td = float(cols[9].text.strip())  # Kick Return TDs

            st_yds_pg = (punt_ret_yds + kick_ret_yds) / games_played  # Sum Yards per Game
            st_td_pg = (punt_ret_td + kick_ret_td) / games_played  # Sum TDs per Game

            data.append({
                'team_name': team_name,
                'st_yds_pg': st_yds_pg,
                'st_td_pg': st_td_pg
            })

    return data


def update_database(data, year):  # Assuming year is 2023 if not specified
    for entry in data:
        try:
            cursor.execute("""
                UPDATE [dbo].[Football-Stats]
                SET st_yds_pg = CAST(? AS DECIMAL(10,3)), st_td_pg = CAST(? AS DECIMAL(10,3))
                WHERE team = ? AND year = ?
            """, (entry['st_yds_pg'], entry['st_td_pg'], entry['team_name'], year))
            conn.commit()
        except Exception as e:
            print(f"Error updating data: {e}")


def main():
    url = "https://www.pro-football-reference.com/years/2023/#all_returns_stats"
    html_content = fetch_html(url)
    if html_content:
        returns_data = parse_returns_stats(html_content)
        if returns_data:
            update_database(returns_data, 2023)
            print("Parsed data successfully.")
        else:
            print("No valid data parsed from the HTML.")
    conn.close()

if __name__ == "__main__":
    main()



