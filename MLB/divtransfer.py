import pandas as pd
from sqlalchemy import create_engine, text

# Database connection using SQLAlchemy
train_db_url = 'mssql+pyodbc://danny1phantom:{pwd}@yoffsornah.database.windows.net:1433/YoffsOrNah-train-MLB?driver=ODBC+Driver+18+for+SQL+Server'
hotstreak_db_url = 'mssql+pyodbc://danny1phantom:{pwd}@yoffsornah.database.windows.net:1433/YoffsOrNah-HotStreak-ChampMLB?driver=ODBC+Driver+18+for+SQL+Server'
train_engine = create_engine(train_db_url)
hotstreak_engine = create_engine(hotstreak_db_url)

def transfer_yoffs_pred():
    # Load yoffs_pred data from the training database
    train_query = "SELECT team, year, div_rnk, lg_rnk FROM [dbo].[Baseball-Training-Stats]"
    train_df = pd.read_sql(train_query, train_engine)
    
    with hotstreak_engine.begin() as conn:
        for index, row in train_df.iterrows():
            team = row['team']
            year = row['year']
            div_rnk = row['div_rnk']
            lg_rnk = row['lg_rnk']
    
            # Update yoffs and yoffs_pred in Basketball-Stats for matching team and year
            conn.execute(
                text("UPDATE [dbo].[Baseball-Stats] SET div_rnk = :div_rnk, lg_rnk = :lg_rnk WHERE team = :team AND year = :year"),
                {'div_rnk': div_rnk, 'lg_rnk': lg_rnk, 'team': team, 'year': year}
            )

# Run the transfer function
if __name__ == "__main__":
    transfer_yoffs_pred()
    print("Rank data transferred successfully.")
