import pandas as pd
from sqlalchemy import create_engine, text

# Database connection using SQLAlchemy
train_db_url = 'mssql+pyodbc://danny1phantom:Popp151565__@yoffsornah.database.windows.net:1433/YoffsOrNah-train-NFL?driver=ODBC+Driver+18+for+SQL+Server'
hotstreak_db_url = 'mssql+pyodbc://danny1phantom:Popp151565__@yoffsornah.database.windows.net:1433/YoffsOrNah-HotStreak-ChampNFL?driver=ODBC+Driver+18+for+SQL+Server'
train_engine = create_engine(train_db_url)
hotstreak_engine = create_engine(hotstreak_db_url)

def transfer_yoffs_pred():
    # Load yoffs_pred data from the training database
    train_query = "SELECT team, year, yoffs, yoffs_pred FROM [dbo].[Football-Predict-Stats]"
    train_df = pd.read_sql(train_query, train_engine)
    
    with hotstreak_engine.begin() as conn:
        for index, row in train_df.iterrows():
            team = row['team']
            year = row['year']
            yoffs = row['yoffs']
            yoffs_pred = row['yoffs_pred']
    
            # Update yoffs and yoffs_pred in Football-Stats for matching team and year
            conn.execute(
                text("UPDATE [dbo].[Football-Stats] SET yoffs = :yoffs, yoffs_pred = :yoffs_pred WHERE team = :team AND year = :year"),
                {'yoffs': yoffs, 'yoffs_pred': yoffs_pred, 'team': team, 'year': year}
            )

# Run the transfer function
if __name__ == "__main__":
    transfer_yoffs_pred()
    print("yoffs_pred data transferred successfully.")
