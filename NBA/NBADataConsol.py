import pyodbc

def update_database():
    conn_str = 'Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-base-NBA;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
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
                conf_stdg,
                DENSE_RANK() OVER (PARTITION BY year ORDER BY win_pct DESC, conf_stdg ASC) AS lg_rank
            FROM [dbo].[Basketball-Stats]
        )
        SELECT
            year,
            team,
            lg_rank
        FROM RankedTeams
    """)
    results = cursor.fetchall()

    # Now, update each row based on the fetched results
    for row in results:
        cursor.execute("""
            UPDATE [dbo].[Basketball-Stats]
            SET
                lg_rank = ?
            WHERE year = ? AND team = ?
        """, (row.lg_rank, row.year, row.team))
        conn.commit()  # Commit after each update or after all updates; depends on transaction size preference

    # Close the connection
    cursor.close()
    conn.close()

# Run the update function
update_database()
