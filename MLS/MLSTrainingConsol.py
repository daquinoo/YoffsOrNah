
import pyodbc

def update_database():
    conn_str = 'Driver={ODBC Driver 18 for SQL Server};Server=tcp:yoffsornah.database.windows.net,1433;Database=YoffsOrNah-train-MLS;Uid=danny1phantom;Pwd={Popp151565__};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Retrieve the data and calculate lg_rnk
    cursor.execute("""
        WITH RankedTeams AS (
            SELECT
                year,
                team,
                win_pct,
                conf_stdg,
                DENSE_RANK() OVER (PARTITION BY year ORDER BY win_pct DESC, conf_stdg ASC) AS lg_rnk
            FROM [dbo].[Soccer-Training-Stats]
        )
        SELECT
            year,
            team,
            lg_rnk
        FROM RankedTeams
    """)
    results = cursor.fetchall()

    # Update each row with the calculated lg_rnk
    for row in results:
        cursor.execute("""
            UPDATE [dbo].[Soccer-Training-Stats]
            SET
                lg_rnk = ?
            WHERE year = ? AND team = ?
        """, (row.lg_rnk, row.year, row.team))
        conn.commit()  # Commit after each update

    # Close the connection
    cursor.close()
    conn.close()

# Run the update function
update_database()

