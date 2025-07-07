import requests
from bs4 import BeautifulSoup, Comment
import pyodbc
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

# Scrapfly setup
SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'  # Replace with your Scrapfly API key
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection setup
conn = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-HotStreak-ChampMLB;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
cursor = conn.cursor()

# Define team URLs for MLB, including historical names
team_base_urls = {
    'Orioles': 'BAL',
    'Tampa Bay Rays': 'TBR',
    'Tampa Bay Devil Rays': 'TBD',
    'Blue Jays': 'TOR',
    'Yankees': 'NYY',
    'Red Sox': 'BOS',
    'Twins': 'MIN',
    'Tigers': 'DET',
    'Cleveland': 'CLE',
    'White Sox': 'CHW',
    'Royals': 'KCR',
    'Astros': 'HOU',
    'Rangers': 'TEX',
    'Mariners': 'SEA',
    'Los Angeles Angels': 'LAA',
    'Anaheim Angels': 'ANA',
    'Athletics': 'OAK',
    'Braves': 'ATL',
    'Phillies': 'PHI',
    'Miami Marlins': 'MIA',
    'Florida Marlins': 'FLA',
    'Mets': 'NYM',
    'Nationals': 'WSN',
    'Montreal Expos': 'MON',
    'Brewers': 'MIL',
    'Cubs': 'CHC',
    'Reds': 'CIN',
    'Pirates': 'PIT',
    'Cardinals': 'STL',
    'Dodgers': 'LAD',
    'Diamondbacks': 'ARI',
    'Padres': 'SDP',
    'Giants': 'SFG',
    'Rockies': 'COL'
}

def fetch_html(url):
    while True:
        try:
            print(f"Fetching URL: {url}")
            api_response: ScrapeApiResponse = scrapfly_client.scrape(scrape_config=ScrapeConfig(
                url=url,
                render_js=True,
                asp=True
            ))
            return api_response.content
        except Exception as e:
            print(f"Scrapfly error: {e}. Retrying...")


def parse_series_info(soup, year):
    series_info = soup.find('div', {'id': 'meta'}).find('h1').get_text(separator=' ', strip=True)
    match = re.match(r'.*?(Series|NLCS|ALCS|Game) (.*?) over (.*?) \((\d+)-(\d+)\)', series_info)
    if match:
        team1 = match.group(2).strip()
        team2 = match.group(3).strip()
        team1_wins = int(match.group(4))
        team2_wins = int(match.group(5))
        total_games = team1_wins + team2_wins
        print(f"Year: {year}, Team1: {team1}, Team2: {team2}, Team1 Wins: {team1_wins}, Team2 Wins: {team2_wins}, Total Games: {total_games}")
        return year, team1, team2, team1_wins, team2_wins, total_games
    print(f"Failed to match series info for year: {year}")
    return None, None, None, None, None, None

def get_table_from_soup(soup, table_id):
    table = soup.find('table', {'id': table_id})
    if table:
        return table
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        table = comment_soup.find('table', {'id': table_id})
        if table:
            return table
    return None

def parse_stats(soup, team_abbr):
    batting_table = get_table_from_soup(soup, f'post_batting_{team_abbr}')
    pitching_table = get_table_from_soup(soup, f'post_pitching_{team_abbr}')
    
    if not batting_table or not pitching_table:
        print(f"Failed to find tables for team: {team_abbr}")
        return None

    batting_stats = batting_table.find('tfoot').find('tr')
    pitching_stats = pitching_table.find('tfoot').find('tr')
    
    stats = {
        'batting': {
            'R': float(batting_stats.find('td', {'data-stat': 'R'}).text),
            'H': float(batting_stats.find('td', {'data-stat': 'H'}).text),
            '2B': float(batting_stats.find('td', {'data-stat': '2B'}).text),
            '3B': float(batting_stats.find('td', {'data-stat': '3B'}).text),
            'HR': float(batting_stats.find('td', {'data-stat': 'HR'}).text),
            'RBI': float(batting_stats.find('td', {'data-stat': 'RBI'}).text),
            'BB': float(batting_stats.find('td', {'data-stat': 'BB'}).text),
            'BA': float(batting_stats.find('td', {'data-stat': 'batting_avg'}).text),
            'OBP': float(batting_stats.find('td', {'data-stat': 'onbase_perc'}).text),
            'SLG': float(batting_stats.find('td', {'data-stat': 'slugging_perc'}).text),
            'SB': float(batting_stats.find('td', {'data-stat': 'SB'}).text),
            'CS': float(batting_stats.find('td', {'data-stat': 'CS'}).text)
        },
        'pitching': {
            'ERA': float(pitching_stats.find('td', {'data-stat': 'earned_run_avg'}).text),
            'H': float(pitching_stats.find('td', {'data-stat': 'H'}).text),
            'R': float(pitching_stats.find('td', {'data-stat': 'R'}).text),
            'SO': float(pitching_stats.find('td', {'data-stat': 'SO'}).text),
            'BB': float(pitching_stats.find('td', {'data-stat': 'BB'}).text),
        }
    }
    return stats

def insert_series_data(year, team, stats, total_games, win_pct, game_offset, opp_hr_pg):
    cursor.execute("""
        INSERT INTO [dbo].[Baseball-Stats] (
            year, team, games_played, win_pct, runs_pg, hits_pg, xbh_pg, HR_pg, RBI_pg,
            team_BB, team_BA, team_OBP, team_SLG, team_SB_pg, team_CS_pg, ERA, team_H_all,
            team_runs_all, team_SO, team_BB_all, team_HR_all, yoffs
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        year, team, total_games + game_offset, win_pct, stats['batting']['R'] / total_games, 
        stats['batting']['H'] / total_games, (stats['batting']['2B'] + stats['batting']['3B'] + stats['batting']['HR']) / total_games, 
        stats['batting']['HR'] / total_games, stats['batting']['RBI'] / total_games, 
        stats['batting']['BB'], stats['batting']['BA'], stats['batting']['OBP'], 
        stats['batting']['SLG'], stats['batting']['SB'] / total_games, stats['batting']['CS'] / total_games, 
        stats['pitching']['ERA'], stats['pitching']['H'] / total_games, stats['pitching']['R'] / total_games, 
        stats['pitching']['SO'] / total_games, stats['pitching']['BB'] / total_games, opp_hr_pg, 1
    ))
    conn.commit()

def main():
    playoff_rounds = ['WC', 'DS', 'CS', 'WS']
    years = range(2012, 2024)
    
    for year in years:
        for round_ in playoff_rounds:
            round_urls = []
            if round_ == 'WC':
                if 2000 <= year <= 2011:
                    continue
                elif 2012 <= year <= 2019 or year == 2021:
                    round_urls.append(f"https://www.baseball-reference.com/postseason/{year}_ALWC.shtml")
                    round_urls.append(f"https://www.baseball-reference.com/postseason/{year}_NLWC.shtml")
                elif year == 2020:
                    round_urls += [f"https://www.baseball-reference.com/postseason/{year}_ALWC{i}.shtml" for i in range(1, 5)]
                    round_urls += [f"https://www.baseball-reference.com/postseason/{year}_NLWC{i}.shtml" for i in range(1, 5)]
                else:
                    round_urls += [f"https://www.baseball-reference.com/postseason/{year}_ALWC{i}.shtml" for i in range(1, 3)]
                    round_urls += [f"https://www.baseball-reference.com/postseason/{year}_NLWC{i}.shtml" for i in range(1, 3)]
            else:
                if round_ == 'WS':
                    round_urls.append(f"https://www.baseball-reference.com/postseason/{year}_{round_}.shtml")
                elif round_ == 'CS':
                    round_urls.append(f"https://www.baseball-reference.com/postseason/{year}_AL{round_}.shtml")
                    round_urls.append(f"https://www.baseball-reference.com/postseason/{year}_NL{round_}.shtml")
                else:
                    round_urls += [f"https://www.baseball-reference.com/postseason/{year}_AL{round_}{i}.shtml" for i in range(1, 3)]
                    round_urls += [f"https://www.baseball-reference.com/postseason/{year}_NL{round_}{i}.shtml" for i in range(1, 3)]

            for url in round_urls:
                html_content = fetch_html(url)
                soup = BeautifulSoup(html_content, 'html.parser')

                # Pass the year directly to parse_series_info
                _, team1, team2, team1_wins, team2_wins, total_games = parse_series_info(soup, year)
                if not team1 or not team2:
                    continue

                team1_abbr = next((abbr for name, abbr in team_base_urls.items() if name in team1), None)
                team2_abbr = next((abbr for name, abbr in team_base_urls.items() if name in team2), None)
                print(f"Team1: {team1}, Team1 Abbreviation: {team1_abbr}")
                print(f"Team2: {team2}, Team2 Abbreviation: {team2_abbr}")
                
                stats_team1 = parse_stats(soup, team1_abbr)
                stats_team2 = parse_stats(soup, team2_abbr)
                if not stats_team1 or not stats_team2:
                    print(f"Failed to find stats for Team1: {team1} or Team2: {team2}")
                    continue

                win_pct_team1 = team1_wins / total_games
                win_pct_team2 = team2_wins / total_games
                opp_hr_pg_team1 = stats_team2['batting']['HR'] / total_games
                opp_hr_pg_team2 = stats_team1['batting']['HR'] / total_games

                cursor.execute("SELECT MAX(games_played) FROM [dbo].[Baseball-Stats] WHERE year=? AND team=?", (year, team1))
                game_offset_team1 = cursor.fetchone()[0] or 0
                cursor.execute("SELECT MAX(games_played) FROM [dbo].[Baseball-Stats] WHERE year=? AND team=?", (year, team2))
                game_offset_team2 = cursor.fetchone()[0] or 0

                insert_series_data(year, team1, stats_team1, total_games, win_pct_team1, game_offset_team1, opp_hr_pg_team1)
                insert_series_data(year, team2, stats_team2, total_games, win_pct_team2, game_offset_team2, opp_hr_pg_team2)

                print(f"Processed {year} {round_} series between {team1} and {team2}")

        print(f"Finished processing year {year}")

if __name__ == "__main__":
    main()
    conn.close()
