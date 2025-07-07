import pandas as pd
from sqlalchemy import create_engine, text

# Database connection using SQLAlchemy
train_db_url = 'mssql+pyodbc://danny1phantom:Popp151565__@yoffsornah.database.windows.net:1433/YoffsOrNah-train-NFL?driver=ODBC+Driver+18+for+SQL+Server'
hotstreak_db_url = 'mssql+pyodbc://danny1phantom:Popp151565__@yoffsornah.database.windows.net:1433/YoffsOrNah-HotStreak-ChampNFL?driver=ODBC+Driver+18+for+SQL+Server'
train_engine = create_engine(train_db_url)
hotstreak_engine = create_engine(hotstreak_db_url)

def transfer_yoffs_pred():
    # Load yoffs_pred data from the training database
    train_query = "SELECT team, year, cur_div_rnk, lg_rank FROM [dbo].[Football-Training-Stats]"
    train_df = pd.read_sql(train_query, train_engine)
    
    with hotstreak_engine.begin() as conn:
        for index, row in train_df.iterrows():
            team = row['team']
            year = row['year']
            cur_div_rnk = row['cur_div_rnk']
            lg_rank = row['lg_rank']
    
            # Update yoffs and yoffs_pred in Football-Stats for matching team and year
            conn.execute(
                text("UPDATE [dbo].[Football-Stats] SET cur_div_rnk = :cur_div_rnk, lg_rank = :lg_rank WHERE team = :team AND year = :year"),
                {'cur_div_rnk': cur_div_rnk, 'lg_rank': lg_rank, 'team': team, 'year': year}
            )

# Run the transfer function
if __name__ == "__main__":
    transfer_yoffs_pred()
    print("Rank data transferred successfully.")
