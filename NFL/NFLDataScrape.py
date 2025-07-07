import requests
from bs4 import BeautifulSoup
import pyodbc

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-base-NFL;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception("Failed to retrieve the webpage.")

def parse_standings(soup):
    standings = []
    division_rank = 1

    # Iterate over each row in the standings table
    for row in soup.find_all('tr'):
        if 'onecell' in row.get('class', []):
            division_rank = 1  # Reset rank for new division
            continue
        if row.find('th', {'scope': 'row'}):
            team_name_cell = row.find('th', {'scope': 'row'})
            team_name = team_name_cell.text.strip().replace('*', '').replace('+', '')
            win_pct_cell = row.find('td', {'data-stat': 'win_loss_perc'})
            if win_pct_cell:
                win_p = win_pct_cell.text.strip()
                win_pct = float(win_p)
                standings.append((team_name, win_pct, division_rank))
                division_rank += 1

    return standings

def insert_data(year, standings):
    for team_name, win_pct, rank in standings:
        cursor.execute("""
            INSERT INTO [dbo].[Football-Stats] (year, team, win_pct, cur_div_rnk)
            VALUES (?, ?, CAST(? AS DECIMAL(10,3)), ?)
        """, (year, team_name, win_pct, rank))
    conn.commit()

def main():
    url = "https://www.pro-football-reference.com/years/2023/#all_team_stats"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    afc_soup = soup.find('table', {'id': 'AFC'})  # Specific table ID for AFC
    nfc_soup = soup.find('table', {'id': 'NFC'})  # Specific table ID for NFC
    
    if afc_soup and nfc_soup:
        afc_data = parse_standings(afc_soup)
        nfc_data = parse_standings(nfc_soup)
        insert_data(2023, afc_data + nfc_data)
    else:
        print("Error: Could not find AFC or NFC tables in the HTML.")

if __name__ == "__main__":
    main()
    conn.close()
