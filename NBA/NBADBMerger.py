import pandas as pd
from sqlalchemy import create_engine, text

# Database connection strings
train_db_url = 'mssql+pyodbc://danny1phantom:Popp151565__@yoffsornah.database.windows.net:1433/YoffsOrNah-train-NBA?driver=ODBC+Driver+18+for+SQL+Server'
hotstreak_db_url = 'mssql+pyodbc://danny1phantom:Popp151565__@yoffsornah.database.windows.net:1433/YoffsOrNah-HotStreak-ChampNBA?driver=ODBC+Driver+18+for+SQL+Server'

# Connect to the databases
train_engine = create_engine(train_db_url)
hotstreak_engine = create_engine(hotstreak_db_url)

# Fetch all teams and years from the ChampNBA database
query = "SELECT DISTINCT team, year FROM [dbo].[Basketball-Stats]"
teams_years = pd.read_sql(query, hotstreak_engine)

# Loop through each team and year
for index, row in teams_years.iterrows():
    team = row['team']
    year = row['year']
    
    # Check if there are existing rows for the current team and year in ChampNBA
    check_query = text("""
    SELECT COUNT(*) FROM [dbo].[Basketball-Stats]
    WHERE team = :team AND year = :year
    """)
    
    with hotstreak_engine.connect() as hotstreak_conn:
        existing_count = hotstreak_conn.execute(check_query, {'team': team, 'year': year}).scalar()
        
        if existing_count > 0:
            # Fetch data from train-NBA database
            train_query = text("""
            SELECT win_pct, conf_stdg, lg_rank, pts_pg, opp_pts_pg, threes_pg, opp_three_pg,
                   fg_perc, opp_fg_perc, oreb_pg, oreb_pg + dreb_pg AS treb_pg, opp_oreb_pg,
                   opp_oreb_pg + opp_dreb_pg AS opp_treb_pg, ast_pg, opp_ast_pg,
                   fta_pg, opp_fta_pg, ft_perc/100 AS ft_perc, turnovers_pg, opp_to_pg, stls_pg,
                   opp_stls_pg, blocks_pg, opp_blks_pg
            FROM [dbo].[Basketball-Training-Stats]
            WHERE team = :team AND year = :year
            """)
            
            with train_engine.connect() as train_conn:
                result = train_conn.execute(train_query, {'team': team, 'year': year})
                train_data = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            # Add games_played = 5 to the data
            train_data['games_played'] = 5
            train_data['team'] = team
            train_data['year'] = year
            
            # Insert the data back into the ChampNBA database
            train_data.to_sql('Basketball-Stats', hotstreak_engine, if_exists='append', index=False)
            
            print(f"Inserted data for {team} - {year}")

print("Data insertion complete!")
