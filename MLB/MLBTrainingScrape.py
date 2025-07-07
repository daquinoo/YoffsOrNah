from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from bs4 import BeautifulSoup, Comment
import pyodbc
import re

# Initialize Scrapfly client
scrapfly = ScrapflyClient(key='scp-live-c8122bf4379c43f0a0ebd066f2d38b94')

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-MLB;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    try:
        api_response: ScrapeApiResponse = scrapfly.scrape(scrape_config=ScrapeConfig(
            url=url,
            render_js=True,
            asp=True
        ))
        if api_response.status_code == 200:
            return api_response.content
        else:
            print(f"Failed to retrieve the webpage: {url}")
            return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_table(html_content, table_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table', id=table_id)
    if not tables:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if f'id="{table_id}"' in comment:
                table_soup = BeautifulSoup(comment, 'html.parser')
                tables.extend(table_soup.find_all('table', id=table_id))
    return tables

def parse_standings(html_content, table_id):
    tables = parse_table(html_content, table_id)
    standings = []
    for table in tables:
        if table:
            rows = table.find('tbody').find_all('tr')
            for idx, row in enumerate(rows):
                team_cell = row.find('th', {'data-stat': 'team_ID'})
                cols = row.find_all('td')
                win_pct = float(cols[2].text.strip())
                if team_cell:
                    team = team_cell.text.strip()
                    standings.append({'team': team, 'win_pct': win_pct, 'div_rnk': idx + 1})
                else:
                    print(f"Skipping row {idx + 1}: team_cell or win_pct_cell not found")
    return standings

def parse_team_data(html_content):
    data = []
    table_ids = ['teams_standard_batting', 'teams_standard_pitching', 'team_output', 'teams_standard_fielding']
    parsed_tables = {table_id: parse_table(html_content, table_id)[0] for table_id in table_ids}

    for row in parsed_tables['teams_standard_batting'].find('tbody').find_all('tr'):
        cols = row.find_all('td')
        team_data = {
            'team': row.find('th').text.strip(),
            'games_played': int(cols[3].text.strip()),
            'hits_pg': float(cols[7].text.strip()) / int(cols[3].text.strip()),
            'xbh_pg': (float(cols[8].text.strip()) + float(cols[9].text.strip()) + float(cols[10].text.strip())) / int(cols[3].text.strip()),
            'runs_pg': float(cols[2].text.strip()),
            'HR_pg': float(cols[10].text.strip()) / int(cols[3].text.strip()),
            'RBI_pg': float(cols[11].text.strip()) / int(cols[3].text.strip()),
            'totalbases_pg': float(cols[21].text.strip()) / int(cols[3].text.strip()),
            'team_BB': float(cols[14].text.strip()),
            'team_BA': float(cols[16].text.strip()),
            'team_OBP': float(cols[17].text.strip()),
            'team_SLG': float(cols[18].text.strip()),
            'team_SB_pg': float(cols[12].text.strip()) / int(cols[3].text.strip()),
            'team_CS_pg': float(cols[13].text.strip()) / int(cols[3].text.strip())
        }
        data.append(team_data)
    
    # Parsing and adding additional data from other tables (teams_standard_pitching, team_output, teams_standard_fielding)
    for idx, row in enumerate(parsed_tables['teams_standard_pitching'].find('tbody').find_all('tr')):
        cols = row.find_all('td')
        data[idx]['team_H_all'] = float(cols[15].text.strip()) / int(cols[7].text.strip())
        data[idx]['team_HR_all'] = float(cols[18].text.strip()) / int(cols[7].text.strip())
        data[idx]['team_SO'] = float(cols[21].text.strip()) / int(cols[7].text.strip())
        data[idx]['team_BB_all'] = float(cols[19].text.strip()) / int(cols[7].text.strip())
        data[idx]['ERA'] = float(cols[6].text.strip())

    for idx, row in enumerate(parsed_tables['team_output'].find('tbody').find_all('tr')):
        cols = row.find_all('td')
        if cols:
            waa_div = cols[0].find('div', class_='right')
            if waa_div:
                data[idx]['team_WAA'] = float(waa_div.text.strip())

    for idx, row in enumerate(parsed_tables['teams_standard_fielding'].find('tbody').find_all('tr')):
        cols = row.find_all('td')
        data[idx]['team_fld_pct'] = float(cols[12].text.strip())
        data[idx]['team_defeff'] = float(cols[2].text.strip())
        data[idx]['team_RTOT'] = float(cols[13].text.strip())
        data[idx]['team_runs_all'] = float(cols[1].text.strip())

    return data

def merge_data(team_data, standings_data):
    for team in team_data:
        for standings in standings_data:
            if team['team'] == standings['team']:
                team['win_pct'] = standings['win_pct']
                team['div_rnk'] = standings['div_rnk']
                break
    return team_data

def insert_data(year, data):
    for entry in data:
        try:
            cursor.execute("""
                INSERT INTO [dbo].[Baseball-Training-Stats] (year, team, games_played, win_pct, div_rnk,
                                                     hits_pg, xbh_pg, runs_pg, HR_pg, RBI_pg, totalbases_pg,
                                                     team_BB, team_BA, team_OBP, team_SLG, team_SB_pg, team_CS_pg,
                                                     team_fld_pct, team_defeff, team_RTOT, team_WAA,
                                                     team_H_all, team_runs_all, team_HR_all, team_SO, team_BB_all, ERA)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (year, entry['team'], entry['games_played'], entry['win_pct'], entry['div_rnk'],
                  entry['hits_pg'], entry['xbh_pg'], entry['runs_pg'], entry['HR_pg'], entry['RBI_pg'], entry['totalbases_pg'],
                  entry['team_BB'], entry['team_BA'], entry['team_OBP'], entry['team_SLG'], entry['team_SB_pg'], entry['team_CS_pg'],
                  entry['team_fld_pct'], entry['team_defeff'], entry['team_RTOT'], entry['team_WAA'],
                  entry['team_H_all'], entry['team_runs_all'], entry['team_HR_all'], entry['team_SO'], entry['team_BB_all'], entry['ERA']))
            conn.commit()
        except Exception as e:
            print(f"Error inserting data for {entry['team']} in {year}: {e}")

def main():
    years = range(2023, 2023+1)
    for year in years:
        print(f"Processing year: {year}")
        standings_url = f"https://www.baseball-reference.com/leagues/majors/{year}-standings.shtml"
        team_url = f"https://www.baseball-reference.com/leagues/majors/{year}.shtml"
        
        standings_html = fetch_html(standings_url)
        team_html = fetch_html(team_url)
        
        if standings_html and team_html:
            standings_data = []
            standings_data.extend(parse_standings(standings_html, 'standings_E'))
            standings_data.extend(parse_standings(standings_html, 'standings_W'))
            standings_data.extend(parse_standings(standings_html, 'standings_C'))

            team_data = parse_team_data(team_html)
            merged_data = merge_data(team_data, standings_data)
            
            insert_data(year, merged_data)
            print(f"Database updated successfully for the year {year}.")
        else:
            print(f"Failed to fetch HTML content for the year {year}.")
    
    conn.close()

if __name__ == "__main__":
    main()
