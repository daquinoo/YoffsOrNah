import json
from datetime import datetime
import pyodbc
import requests
import pandas as pd
import time

def fetch_stock_data(symbol, api_key):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&apikey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"API request successful for {symbol}!")
        data = response.json()
        return data.get('Time Series (Daily)', {})
    else:
        print(f"API request failed for {symbol} with status code {response.status_code}")
        return None

def process_stock_data(data, end_date, symbol):
    if not data:
        return pd.DataFrame()  # Return empty df

    df = pd.DataFrame.from_dict(data, orient='index')
    df.index = pd.to_datetime(df.index)
    df.sort_index(ascending=False, inplace=True)
    end_date = pd.to_datetime(end_date)
    df = df[df.index >= end_date]
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    df['volume'] = df['volume'].astype(int)
    
    df['symbol'] = symbol
    df['year'] = df.index.year
    df['qtr'] = df.index.quarter
    df['month'] = df.index.strftime('%B')
    df['week'] = (df.index.day - 1) // 7 + 1
    df['day'] = df.index.day
    
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'date'}, inplace=True)
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    return df[['symbol', 'date', 'open', 'close', 'high', 'low', 'volume', 'year', 'qtr', 'month', 'week', 'day']]

def insert_data_to_db(conn, df):
    if df.empty:
        print("No data to insert.")
        return

    cursor = conn.cursor()
    data = [tuple(x) for x in df.to_numpy()]
    cursor.executemany("""
    INSERT INTO [dbo].[HistoricalData]
    (symbol, [date], [open], [close], high, low, volume, year, qtr, month, week, day)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    cursor.close()

if __name__ == "__main__":
    api_key = "CXPSPN3NBC0L5DGO"
    end_date = "2019-05-20"
    
    # Database connection string
    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        "Server=tcp:goldenfleece-dataserver.database.windows.net,1433;"
        "Database=HistoricalStockData;"
        "Uid=danny1phantom;"
        "Pwd=Popp151565__;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )


        #'''"AAPL", "NVDA", "MSFT", "GOOG", "GOOGL", "AMZN", "META", "BRK.B", "LLY", "AVGO",
        #'''"TSLA", "JPM", "WMT", "UNH", "XOM", "V", "MA", "PG", "JNJ", "COST",
        #"ORCL", "HD", "ABBV", "BAC", "KO", "MRK", "NFLX", "CVX", "CRM", "ADBE",
        #"AMD", "PEP", "TMUS", "TMO", "LIN", "ACN", "MCD", "CSCO", "ABT", "DHR",
        #"WFC", "TXN", "QCOM", "PM", "GE", "IBM", "AXP", "AMGN", "VZ", "INTU",
        #ISRG", "NOW", "CAT", "GS", "NEE", "DIS", "MS", "PFE", "AMAT", "RTX",
        #"SPGI", "CMCSA", "UBER", "UNP", "LOW", "PGR", "T", "TJX", "SYK", "LMT",
        #"HON", "COP", "BLK", "REGN", "BKNG", "ELV", "NKE", "VRTX", "PLD", "ETN",
        #"SCHW", "C", "BSX", "MDT", "PANW", "ADI", "CB", "UPS", "ADP", "MMC",
        #"MU", "BX", "SBUX", "ANET", "KKR", "KLAC", "BA", "LRCX", "AMT", "DE",
        #"HCA", "CI", "FI", "BMY", "MDLZ", "GILD", "SO", "ICE", "SHW", "MO",
        #"MCO", "DUK", "INTC", "CL", "WM", "ZTS", "SNPS", "APH", "GD", "CTAS",
        #"TT", "EQIX", "PH", "CMG", "CME", "NOC", "CVS", "PYPL", "EOG", "ITW",
        #"TDG", "AON", "TGT", "ABNB", "FDX", "WELL", "CDNS", "MSI", "MMM", "MCK",
        #"USB", "PNC", "ECL", "BDX", "CSX", "CRWD", "RSG", "ORLY", "CARR", "FCX",
        #"SLB", "NXPI", "MAR", "AJG", "DHI", "APD", "CEG", "AFL", "NEM", "EMR",
        #"PSA", "TFC", "ROP", "MPC", "FTNT", "PSX", "ADSK", "WMB", "NSC", "GM",
        #"SPG", "COF", "AZO", "O", "OXY", "HLT", "AEP", "MET", "SRE", "ROST",
        #"OKE", "CPRT", "TRV", "CHTR", "LEN", "PCAR", "GEV", "BK", "URI", "DLR",
        #"CCI", "KDP", "ALL", "KMB", "AIG", "JCI", "KMI", "D", "GWW", "PAYX",
        #"TEL", "MNST", "VLO", "COR", "IQV", "MSCI", "MPWR", "STZ", "F", "FIS",
        #"KHC", "RCL", "LHX", "AMP", "MCHP", "ODFL", "HUM", "CMI", "HES", "FICO",
        #"PRU", "KVUE", "EW", "CNC", "ACGL", "PCG", "NDAQ", "A", "PEG", "IDXX",
        #"PWR", "HWM", "HSY", "GIS", "EA", "AME", "FAST", "GEHC", "CTVA", "VRSK",
        #"KR", "CTSH", "YUM", "EXC", "DOW", "SYY", "EXR", "OTIS", "EFX", "IT",
        #"IR", "GLW", "NUE", "CBRE", "BKR", "FANG", "ED", "VICI", "HPQ", "GRMN",
        #"XEL", "LULU", "EL", "DD", "MLM", "RMD", "VMC", "DFS", "IRM", "XYL",
        #"HIG", "EIX", "SMCI", "ON", "CSGP", "LYB", "TRGP", "MRNA", "AVB", "CDW",
        #"ROK", "MTD", "LVS", "BIIB", "PPG", "DXCM", "TSCO", "WEC", "BRO", "VST",
        #"EBAY", "ADM", "WTW", "WAB", "FITB", "DVN", "NVR", "GPN", "TTWO", "HAL",
        #PHM", "MTB", "ANSS", "EQR", "K", "AWK", "DG", "VLTO", "AXON", "NTAP",
        #"KEYS", "CAH", "DAL", "DTE", "IFF", "FTV", "FSLR", "ETR", "STT", "DOV",
        #"FE", "CHD", "HPE", "VTR", "BR", "SBAC", "TYL", "TROW", "RJF", "ROL",
        #"DECK", "ES", "SW", "PPL", "ZBH", "STE", "GDDY", "TSN", "WY", "CBOE",
        #"WRB", "AEE", "STX", "LYV", "WST", "INVH", "TER", "BF.B", "WDC", "MKC",
        #"ARE", "PTC", "HBAN", "CCL", "RF", "DLTR", "LDOS", "CINF", "CPAY", "HUBB",
        #"BLDR", "MOH", "WBD", "ATO", "CMS", "WAT", "EQT", "GPC", "TDY", "BALL",
        #"LH", "CFG", "OMC", "BAX", "APTV", "SYF", "BBY", "STLD", "CLX", "FOXA",
        #"ESS", "COO", "J", "DRI", "HOLX", "PFG", "MAA", "PKG", "FOX", "ZBRA",
        #"NTRS", "CTRA", "EXPE", "ULTA", "JBHT", "VRSN", "HRL", "L", "MAS", "AVY",
        #"CNP", "SWKS", "NRG", "EXPD", "DGX", "ALGN", "EG", "IP", "TXT", "LUV",
       #"ENPH", "GEN", "AMCR", "NWS", "MRO", "NWSA", "DOC", "KIM", "KEY", "FDS",
        #"UHS", "SWK", "IEX", "AKAM", "CPB", "RVTY", "DPZ", "SNA", "LNT", "CAG",
        #"CF", "NDSN", "NI","CE", "PNR", "UDR", "BG", "UAL", "VTRS", "TRMB",
        #"POOL", "EVRG", "KMX", "CPT", "DVA", "SJM", "REG", "PODD", "JNPR", "AES",
        #"INCY", "JBL", "JKHY", "IPG", "HST", "AOS", "CHRW", "ALLE", "EMN", "BXP",
        #"FFIV", "MGM", "TFX", "EPAM", "TECH", "LKQ", "TAP", "HII", "BEN", "CTLT",
        #"QRVO", "RL", "APA", "CRL", "ALB", "SOLV", "AIZ", "MHK", "PNW", "FRT",
        #"MTCH", "HAS", "GNRC", "TPR", "DAY", "GL", "MOS", "PAYC", "HSIC", "WBA",
        #"LW", "MKTX", "BIO", "WYNN", "FMC", "CZR", "BWA", "BBWI", "IVZ", "NCLH",
        #"PARA", "AAL", "ETSY"     
    '''"RHI",
    "CMA",
    "ILMN",
    "PXD",
    "XRAY",
    "VFC",
    "WHR",
    "ZION",
    "SEE",
    "ALK",
    "SEDG",
    "OGN",
    "ATVI",
    "DXC",
    "LNC",
    "NWL",
    "AAP",
    "DISH",
    "FRCB",
    "LUMN",
    "SBNY",
    "SIVB",
    "FRCB",
    "VNO",
    "ABMD",
    "FBHS",
    "MBC",
    "AGCL",
    "TWTR",
    "NLSN",
    "CTXS",
    "DRE",
    "PVH",
    "PENN",
    "UA",
    "UAA",
    "IPGP",
    "CERN",
    "PBCT",
    "INFO",
    "XLNX",
    "SBNY",
    "GAP",
    "BFH",
    "HOG",
    "LEG",
    "SEDG",
    "HBI",
    "WU",
    "KSU",
    "CDAY",
    "PRGO",
    "UNM",
    "NOV",
    "MXIM",
    "ALXN",
    "HFC",
    "OGN",
    "FLIR",
    "VAR",
    "FLS",
    '''
        
    # Full list of dropped S&P symbols
    symbols = [
    "DINO",
    "SLG",
    "XRX",
    "VNT",
    "FTI",
    "CXO",
    "TIF",
    "AIV",
    "NBL",
    "VNT",
    "ETFC",
    "HRB",
    "COTY",
    "KSS",
    "JWN",
    "HP",
    "CPRI",
    "AGN",
    "M",
    "RTN",
    "ARNC",
    "XEC",
    "WCG",
    "AMG",
    "TRIP",
    "MAC",
    "STI",
    "VIAB",
    "CELG",
    "NKTR",
    "JEF",
    "TSS",
    "APC",
    "FL",
    "RHT",
    "LLL",
    "BMS",
    "MAT",
    "DWDP",
    "FLR"
]
    
    try:
        conn = pyodbc.connect(conn_str)
        for i, symbol in enumerate(symbols, 1):
            print(f"Processing {symbol} ({i}/{len(symbols)})...")
            
            api_symbol = symbol.replace('.', '-') if '.' in symbol else symbol
            
            raw_data = fetch_stock_data(api_symbol, api_key)
            if raw_data:
                df_processed = process_stock_data(raw_data, end_date, symbol)
                insert_data_to_db(conn, df_processed)
                print(f"Data inserted for {symbol}. Processed {len(df_processed)} entries.")
            else:
                print(f"No data available for {symbol}")
            
            # Sleep to avoid  rate limit (75 calls per minute)
            if i % 75 == 0:
                time.sleep(60)  # Wait 60 sec after every 75 calls
    except pyodbc.Error as e:
        print(f"A database error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

    print("Processing completed for all symbols.")