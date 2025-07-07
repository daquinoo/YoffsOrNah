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

def parse_divisions(soup):
    divisions = {}
    current_division = None

    for row in soup.find_all('tr'):
        if 'thead' in row.get('class', []) and 'onecell' in row.get('class', []):
            current_division = row.find('td', {'data-stat': 'onecell'}).text.strip()
        elif current_division and row.find('th', {'scope': 'row'}):
            team_name_cell = row.find('th', {'scope': 'row'})
            team_name = team_name_cell.text.strip().replace('*', '').replace('+', '')
            divisions[team_name] = current_division

    return divisions

def update_division_data(divisions):
    for team_name, division in divisions.items():
        cursor.execute("""
            UPDATE [dbo].[Football-Stats]
            SET div = ?
            WHERE team = ?
        """, (division, team_name))
    conn.commit()

def main():
    url = "https://www.pro-football-reference.com/years/2023/"
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    afc_soup = soup.find('table', {'id': 'AFC'})  # Specific table ID for AFC
    nfc_soup = soup.find('table', {'id': 'NFC'})  # Specific table ID for NFC
    
    if afc_soup and nfc_soup:
        afc_divisions = parse_divisions(afc_soup)
        nfc_divisions = parse_divisions(nfc_soup)
        divisions = {**afc_divisions, **nfc_divisions}
        update_division_data(divisions)
    else:
        print("Error: Could not find AFC or NFC tables in the HTML.")

if __name__ == "__main__":
    main()
    conn.close()
