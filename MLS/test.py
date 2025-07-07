import requests
from bs4 import BeautifulSoup, Comment
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyodbc
import re
import time

# Database connection setup
conn = pyodbc.connect(
    'Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;'
    'Database=YoffsOrNah-base-MLS;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;'
    'TrustServerCertificate=no;Connection Timeout=30;'
)
cursor = conn.cursor()

def fetch_html_with_selenium(url, switchers):
    # Initialize the Chrome WebDriver
    service = ChromeService()
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)

    html_content = driver.page_source

    for table_id, switcher_data_show in switchers.items():
        try:
            # Wait for the switcher to be clickable and then click it
            switcher = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f'a.sr_preset[data-show="{switcher_data_show}"]'))
            )
            driver.execute_script("arguments[0].scrollIntoView();", switcher)  # Scroll into view
            switcher.click()
            time.sleep(2)  # Wait for the table to load

            # Fetch the updated HTML content after each switcher click
            html_content = driver.page_source
        except Exception as e:
            print(f"Error triggering switcher for {table_id}: {e}")

    driver.quit()
    return html_content

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
    cursor.execute("SELECT team, games_played FROM [dbo].[Soccer-Stats]")
    games_played = {row.team: row.games_played for row in cursor.fetchall()}
    return games_played

def parse_team_data(html_content, games_played):
    data = {}
    table_ids = [
        'stats_squads_standard_against', 
        'stats_squads_keeper_adv_against', 
        'stats_squads_passing_against', 
        'stats_squads_possession_against', 
        'stats_squads_misc_against',
        'stats_squads_gca_against'
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

                if table_id == 'stats_squads_standard_against':
                    data[team].update({
                        'ga_pg': float(cols[7].text.strip()) / gp,
                        'pkconc_pg': float(cols[12].text.strip()) / gp
                    })
                elif table_id == 'stats_squads_keeper_adv_against':
                    data[team].update({
                        'setp_g_pg': (float(cols[3].text.strip()) + float(cols[4].text.strip()) + float(cols[5].text.strip())) / gp,
                        'opp_spg_pg': (float(cols[3].text.strip()) + float(cols[4].text.strip()) + float(cols[5].text.strip())) / gp
                    })
                elif table_id == 'stats_squads_passing_against':
                    data[team].update({
                        'opp_pass_prc': float(cols[4].text.strip()),
                        'opp_kp_pg': float(cols[20].text.strip()) / gp
                    })
                elif table_id == 'stats_squads_possession_against':
                    data[team].update({
                        'opp_poss_prc': float(cols[1].text.strip()),
                        'opp_tko_perc': float(cols[12].text.strip())
                    })
                elif table_id == 'stats_squads_misc_against':
                    data[team].update({
                        'opp_owng_pg': float(cols[13].text.strip()) / gp
                    })
                elif table_id == 'stats_squads_gca_against':
                    data[team].update({
                        'opp_sca_pg': float(cols[2].text.strip()) / gp
                    })
    return list(data.values())

def update_data(data):
    for entry in data:
        try:
            cursor.execute("""
                UPDATE [dbo].[Soccer-Stats]
                SET ga_pg = ?, pkconc_pg = ?, setp_g_pg = ?, opp_spg_pg = ?, opp_pass_prc = ?, opp_kp_pg = ?, 
                    opp_poss_prc = ?, opp_tko_perc = ?, opp_owng_pg = ?, opp_sca_pg = ?
                WHERE team = ?
            """, (
                entry.get('ga_pg'), entry.get('pkconc_pg'), entry.get('setp_g_pg'), entry.get('opp_spg_pg'), 
                entry.get('opp_pass_prc'), entry.get('opp_kp_pg'), entry.get('opp_poss_prc'), 
                entry.get('opp_tko_perc'), entry.get('opp_owng_pg'), entry.get('opp_sca_pg'), entry['team']
            ))
            conn.commit()
        except Exception as e:
            print(f"Error updating data for {entry['team']}: {e}")

def main():
    url = "https://fbref.com/en/comps/22/2023/2023-Major-League-Soccer-Stats"
    switchers = {
        'stats_squads_standard_against': '.assoc_stats_squads_standard_against',
        'stats_squads_keeper_adv_against': '.assoc_stats_squads_keeper_adv_against',
        'stats_squads_passing_against': '.assoc_stats_squads_passing_against',
        'stats_squads_possession_against': '.assoc_stats_squads_possession_against',
        'stats_squads_misc_against': '.assoc_stats_squads_misc_against',
        'stats_squads_gca_against': '.assoc_stats_squads_gca_against'
    }
    html_content = fetch_html_with_selenium(url, switchers)
    if html_content:
        games_played = get_games_played()
        stats_data = parse_team_data(html_content, games_played)
        update_data(stats_data)
        print("Team stats updated successfully.")
    else:
        print("Failed to fetch HTML content.")
    conn.close()

if __name__ == "__main__":
    main()
