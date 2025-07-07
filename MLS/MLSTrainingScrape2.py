from asyncio.windows_events import NULL
import pyodbc
import re
from bs4 import BeautifulSoup, Comment
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Initialize Scrapfly client with your API key
scrapfly = ScrapflyClient(key='scp-live-c8122bf4379c43f0a0ebd066f2d38b94')

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-MLS;Uid=danny1phantom;Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

def fetch_html(url):
    api_response: ScrapeApiResponse = scrapfly.scrape(scrape_config=ScrapeConfig(
        url=url,
        render_js=True,
        asp=True
    ))
    if api_response.status_code == 200:
        return api_response.content
    else:
        print(f"Failed to retrieve the webpage: {api_response.status_code}")
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
        tbody = soup.find('table', id=table_id).find('tbody')
        return tbody

def get_games_played():
    cursor.execute("SELECT team, games_played FROM [dbo].[Soccer-Training-Stats]")
    games_played = {row.team: row.games_played for row in cursor.fetchall()}
    return games_played

def parse_team_data(html_content, games_played):
    data = {}
    table_ids = [
        'stats_squads_standard_for', 'stats_squads_keeper_for', 
        'stats_squads_keeper_adv_for', 'stats_squads_shooting_for', 
        'stats_squads_passing_for', 'stats_squads_defense_for', 
        'stats_squads_possession_for', 'stats_squads_misc_for', 
        'stats_squads_gca_for'
    ]

    parsed_tables = {table_id: parse_stats(html_content, table_id) for table_id in table_ids}

    for table_id in table_ids:
        for row in parsed_tables[table_id].find_all('tr'):
            cols = row.find_all('td')
            team = re.sub(r'[\*\xa0]', '', row.find('th', {'data-stat': 'team'}).text).strip()
            if team in games_played:
                gp = games_played[team]
                if team not in data:
                    data[team] = {'team': team}

                if table_id == 'stats_squads_standard_for':
                    data[team].update({
                        'pkwon_pg': float(cols[11].text.strip()) / gp,
                        'pkconv_perc': float(cols[11].text.strip()) / float(cols[12].text.strip()) if float(cols[12].text.strip()) != 0 else 0
                    })
                elif table_id == 'stats_squads_keeper_for':
                    data[team].update({
                        'save_per': float(cols[9].text.strip()),
                        'pksave_perc': float(cols[19].text.strip()) if float(cols[15].text.strip()) != 0 else 100
                    })
                elif table_id == 'stats_squads_keeper_adv_for':
                    data[team].update({
                        'setp_g_pg': (float(cols[3].text.strip()) + float(cols[4].text.strip()) + float(cols[5].text.strip())) / gp,
                    })
                elif table_id == 'stats_squads_shooting_for':
                    data[team].update({
                        'shots_ot_pg': float(cols[4].text.strip()) / gp
                    })
                elif table_id == 'stats_squads_gca_for':
                    data[team].update({
                        'sca_pg': float(cols[2].text.strip()) / gp
                    })
                elif table_id == 'stats_squads_passing_for':
                    data[team].update({
                        'cmp_pass_prc': float(cols[4].text.strip()),
                        'keypass_pg': float(cols[20].text.strip()) / gp
                    })
                elif table_id == 'stats_squads_possession_for':
                    data[team].update({
                        'poss_prc': float(cols[1].text.strip()),
                        'takeon_perc': float(cols[12].text.strip())
                    })
                elif table_id == 'stats_squads_defense_for':
                    data[team].update({
                        'err_pg': float(cols[17].text.strip()) / gp,
                        'tack_int_pg': float(cols[15].text.strip()) / gp,
                        'tack_per': float(cols[9].text.strip()),
                        'shots_blocked_pg': float(cols[12].text.strip()) / gp
                    })
                elif table_id == 'stats_squads_misc_for':
                    data[team].update({
                        'aerial_perc': float(cols[17].text.strip()),
                        'cross_pg': float(cols[8].text.strip()) / gp,
                        'owng_conc_pg': float(cols[13].text.strip()) / gp,
                        'looseballs_rec_pg': float(cols[14].text.strip()) / gp,
                        'fls_pg': float(cols[5].text.strip()) / gp,
                        'fld_pg': float(cols[6].text.strip()) / gp,
                        'pkconc_pg': float(cols[12].text.strip()) / gp
                    })
    return list(data.values())

def update_data(data):
    for entry in data:
        try:
            cursor.execute("""
                UPDATE [dbo].[Soccer-Training-Stats]
                SET pkwon_pg = ?, pkconv_perc = ?, sca_pg = ?, pkconc_pg = ?, save_per = ?, pksave_perc = ?, setp_g_pg = ?, shots_ot_pg = ?, cmp_pass_prc = ?, keypass_pg = ?, poss_prc = ?, takeon_perc = ?, err_pg = ?, tack_int_pg = ?, tack_per = ?, shots_blocked_pg = ?, aerial_perc = ?, cross_pg = ?, owng_conc_pg = ?, looseballs_rec_pg = ?, fls_pg = ?, fld_pg = ?
                WHERE team = ?
            """, (entry.get('pkwon_pg'), entry.get('pkconv_perc'), entry.get('sca_pg'), entry.get('pkconc_pg'),
                  entry.get('save_per'), entry.get('pksave_perc'), entry.get('setp_g_pg'), entry.get('shots_ot_pg'),
                  entry.get('cmp_pass_prc'), entry.get('keypass_pg'), entry.get('poss_prc'),
                  entry.get('takeon_perc'), entry.get('err_pg'), entry.get('tack_int_pg'),
                  entry.get('tack_per'), entry.get('shots_blocked_pg'), entry.get('aerial_perc'), 
                  entry.get('cross_pg'), entry.get('owng_conc_pg'), entry.get('looseballs_rec_pg'), 
                  entry.get('fls_pg'), entry.get('fld_pg'), entry['team']))
            conn.commit()
        except Exception as e:
            print(f"Error updating data for {entry['team']}: {e}")

def main():
    for year in range(2018, 2023+1):
        url = f"https://fbref.com/en/comps/22/{year}/{year}-Major-League-Soccer-Stats"
        html_content = fetch_html(url)
        if html_content:
            games_played = get_games_played()
            stats_data = parse_team_data(html_content, games_played)
            update_data(stats_data)
            print(f"Team stats for {year} updated successfully.")
        else:
            print(f"Failed to fetch HTML content for {year}.")
    conn.close()

if __name__ == "__main__":
    main()
