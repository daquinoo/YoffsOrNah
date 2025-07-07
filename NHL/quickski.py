import re
from datetime import datetime
from bs4 import BeautifulSoup
import pyodbc
import requests
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY_API_KEY = 'scp-live-c8122bf4379c43f0a0ebd066f2d38b94'
scrapfly_client = ScrapflyClient(key=SCRAPFLY_API_KEY)

# Database connection string
conn_str = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=tcp:goldenfleece-dataserver.database.windows.net,1433;"
    "Database=InsiderTrades;"
    "Uid=danny1phantom;"
    "Pwd={Popp151565__};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

# List of symbols
symbols = [
    "GAP", "BFH", "FRCB"
]

#need to do "GAP", "BFH", "FRCB", "DINO",

def fetch_html(url):
    while True:
        try:
            print(f"Fetching URL: {url}")
            api_response: ScrapeApiResponse = scrapfly_client.scrape(scrape_config=ScrapeConfig(
                url=url,
                render_js=True,
                asp=True
            ))
            #if "#google_vignette" in api_response.context['url']:
            #    print("Detected ad redirect. Retrying...")
            #    continue
            return api_response.content
        except Exception as e:
            print(f"Scrapfly error: {e}. Retrying...")

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%d %b %Y').strftime('%m-%d-%Y')
    except ValueError:
        print(f"Error parsing date: {date_str}")
        return None

def get_trade_size(trade_amt):
    size_map = {
        (1000, 15000): 2,
        (15000, 50000): 3,
        (50000, 100000): 4,
        (100000, 250000): 5,
        (250000, 500000): 6,
        (500000, 1000000): 7,
        (1000000, 5000000): 8,
        (5000000, 25000000): 9,
        (25000000, 100000000): 10,
        (100000000, 500000000): 11,
        (500000000, 1000000000): 12,
        (1000000000, float('inf')): 13
    }
    for (lower, upper), size in size_map.items():
        if lower <= trade_amt < upper:
            return size
    return 1  # For amounts less than 1K

def format_insider_name(name):
    name = name.replace(',', '').strip()
    company_keywords = ["l.p.", "fund", "capital", "holdings", "trust", "llc", "s.c.a.", "s.a.r.l.", "authority", "empresarial", "international", "capitales", "foundation", "investment", "partners", "co", "management", "co.", "llc.", "insurance", "corp", "corporation", "inc", "inc.", "equity", "lp", "partnership", "association", "corp.", "ltd", "ltd.", "financial", "advisors", "credit", "venture", "ventures", "strategic", "ag", "a.g.", "limited", "partnerships", ]
    if any(word.lower() in name.lower() for word in company_keywords):
        return name
    name_parts = name.split()
    if any(part.lower() in ["phd", "ii", "jr", "iii"] for part in name_parts):
        for i, part in enumerate(name_parts):
            if part.lower() in ["ii", "iii", "jr", "phd"]:
                return " ".join(name_parts[1:i] + [name_parts[0]] + name_parts[i:])
    return " ".join(name_parts[1:] + [name_parts[0]])

def parse_date(date_str):
    try:
        if isinstance(date_str, list):
            date_str = ' '.join(date_str)
        #print(f"Parsing date: {date_str}")
        parsed_date = datetime.strptime(date_str, '%d %b %Y').strftime('%m-%d-%Y')
        #print(f"Parsed date: {parsed_date}")
        return parsed_date
    except ValueError as e:
        print(f"Error parsing date: {date_str}. Error: {e}")
        return None

def parse_trade(row, symbols):
    try:
        symbol = row.select_one('td.iss_sym a').text.strip()
        if symbol not in symbols:
            print(symbol)
            return None

        insider = format_insider_name(row.select_one('td.rep_name a').text.strip())
        relation = row.select_one('td.rel').text.strip()
        tenPerc = 0
        if "10%" in relation:
            tenPerc = 1
            # Split by comma and find the part containing "10%"
            parts = relation.split(',')
            for i, part in enumerate(parts):
                if "10%" in part:
                    # Remove this part and any following parts
                    relation = ','.join(parts[:i])
                    break
        
        # Trim any remaining whitespace
        relation = relation.strip()

        pDate_elem = row.select_one('td.f_date a')
        #print(f"pDate element: {pDate_elem}")
        if pDate_elem:
            pDate_text = ' '.join(pDate_elem.text.split()[:3])
            #print(f"pDate text: {pDate_text}")
            pDate = parse_date(pDate_text)
        else:
            print("pDate element not found")
            return None

        tDate_elem = row.select_one('td.t_date')
        #print(f"tDate element: {tDate_elem}")
        if tDate_elem:
            tDate_text = tDate_elem.text.strip()
            #print(f"tDate text: {tDate_text}")
            tDate = parse_date(tDate_text)
        else:
            print("tDate element not found")
            return None

        tradeType_elem = row.select_one('td.tran_code')
        tradeType = "BUY" if "green" in tradeType_elem.get('class', []) else "SELL"
        amendment = 1 if tradeType_elem.select_one('span') and tradeType_elem.select_one('span').text.strip() == 'A' else 0

        amtShares = float(row.select_one('td.sh').text.replace(',', ''))
        priceSec = float(row.select_one('td.pr').text.replace(',', ''))
        tradeAmt = float(row.select_one('td.amt').text.replace(',', ''))
        tradeSize = get_trade_size(tradeAmt)

        direct = 1 if row.select_one('td.dir_ind').text.strip() == 'D' else 0

        date_obj = datetime.strptime(pDate, '%m-%d-%Y')
        year = date_obj.year
        qtr = (date_obj.month - 1) // 3 + 1
        month = date_obj.strftime('%B')
        week = (date_obj.day - 1) // 7 + 1
        day = date_obj.day

        return {
            'insider': insider,
            'relation': relation,
            'tenPerc': tenPerc,
            'symbol': symbol,
            'pDate': pDate,
            'tDate': tDate,
            'tradeType': tradeType,
            'amendment': amendment,
            'tradeAmt': tradeAmt,
            'tradeSize': tradeSize,
            'priceSec': priceSec,
            'amtShares': amtShares,
            'direct': direct,
            'year': year,
            'qtr': qtr,
            'month': month,
            'week': week,
            'day': day
        }
    except Exception as e:
        print(f"Error parsing trade: {e}")
        return None

def insert_trade(conn, trade):
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO [dbo].[GenInsiderTrades]
    (insider, relation, tenPerc, symbol, pDate, tDate, tradeType, amendment, tradeAmt, tradeSize, priceSec, amtShares, direct, year, qtr, month, week, day)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade['insider'], trade['relation'], trade['tenPerc'], trade['symbol'],
        trade['pDate'], trade['tDate'], trade['tradeType'], trade['amendment'],
        trade['tradeAmt'], trade['tradeSize'], trade['priceSec'], trade['amtShares'],
        trade['direct'], trade['year'], trade['qtr'], trade['month'], trade['week'], trade['day']
    ))
    conn.commit()

def main():
    conn = pyodbc.connect(conn_str)
    
    for page in range(1, 2107):
        url = f"https://www.dataroma.com/m/ins/ins.php?t=y2&am=0&sym=&o=fd&d=d&L={page}"
        html = fetch_html(url)
        if not html:
            continue
        
        soup = BeautifulSoup(html, 'html.parser')
        trade_rows = soup.select('table#grid tr.col1, table#grid tr.col2')
        
        if not trade_rows:
            print(f"No trades found on page {page}. Ending scraping.")
            break
        
        trades_processed = 0
        for row in trade_rows:
            trade = parse_trade(row, symbols)
            if trade:
                insert_trade(conn, trade)
                print(f"Processed trade: {trade['insider']} - {trade['symbol']} - {trade['relation']} - {trade['tenPerc']} - {trade['pDate']} - {trade['tDate']} - {trade['tradeType']} - {trade['amendment']} - {trade['tradeAmt']} - {trade['tradeSize']} - {trade['priceSec']} - {trade['amtShares']} - {trade['direct']} - {trade['year']} - {trade['qtr']} - {trade['month']} - {trade['week']} - {trade['day']}")
                trades_processed += 1
            else:
                print("Skipped a trade (symbol not in list or missing data)")
                trades_processed += 1
        
        print(f"Processed page {page} - {trades_processed} trades")
    
    conn.close()

if __name__ == "__main__":
    main()