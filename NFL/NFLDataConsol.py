import pyodbc

def update_database():
    conn_str = 'Driver={ODBC Driver 18 for SQL Server};' \
               'Server=tcp:yoffsornah.database.windows.net,1433;' \
               'Database=YoffsOrNah-base-NFL;Uid=danny1phantom;' \
               'Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;' \
               'Connection Timeout=30;'
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # First, retrieve the data to be updated
    cursor.execute("""
        WITH RankedTeams AS (
            SELECT
                year,
                team,
                games_played,
                win_pct,
                cur_div_rnk,
                ROUND((pass_TD_pg + rush_TD_pg + def_TD_per_game + ST_TD_pg), 3) AS total_TD_pg,
                ROUND((pass_TD_all_pg + rush_TD_all_pg + ST_TD_all_pg + def_TD_all_PG), 3) AS TD_allow_pg,
                RANK() OVER (PARTITION BY year ORDER BY win_pct DESC, cur_div_rnk ASC) AS lg_rank
            FROM [dbo].[Football-Stats]
        )
        SELECT
            year,
            team,
            total_TD_pg,
            TD_allow_pg,
            lg_rank
        FROM RankedTeams
    """)
    results = cursor.fetchall()

    # Now, update each row based on the fetched results
    for row in results:
        cursor.execute("""
            UPDATE [dbo].[Football-Stats]
            SET
                total_TD_pg = ?,
                TD_allow_pg = ?,
                lg_rank = ?
            WHERE year = ? AND team = ?
        """, (row.total_TD_pg, row.TD_allow_pg, row.lg_rank, row.year, row.team))
        conn.commit()  # Commit after each update or after all updates; depends on transaction size preference

    # Close the connection
    cursor.close()
    conn.close()

# Run the update function
update_database()
