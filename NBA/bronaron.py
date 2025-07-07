# Define the first and second lists
list1 = [
    "AAPL", "NVDA", "MSFT", "GOOG", "GOOGL", "AMZN", "META", "BRK.B", "LLY", "AVGO",
    "TSLA", "JPM", "WMT", "UNH", "XOM", "V", "MA", "PG", "JNJ", "COST",
    "ORCL", "HD", "ABBV", "BAC", "KO", "MRK", "NFLX", "CVX", "CRM", "ADBE",
    "AMD", "PEP", "TMUS", "TMO", "LIN", "ACN", "MCD", "CSCO", "ABT", "DHR",
    "WFC", "TXN", "QCOM", "PM", "GE", "IBM", "AXP", "AMGN", "VZ", "INTU",
    "ISRG", "NOW", "CAT", "GS", "NEE", "DIS", "MS", "PFE", "AMAT", "RTX",
    "SPGI", "CMCSA", "UBER", "UNP", "LOW", "PGR", "T", "TJX", "SYK", "LMT",
    "HON", "COP", "BLK", "REGN", "BKNG", "ELV", "NKE", "VRTX", "PLD", "ETN",
    "SCHW", "C", "BSX", "MDT", "PANW", "ADI", "CB", "UPS", "ADP", "MMC",
    "MU", "BX", "SBUX", "ANET", "KKR", "KLAC", "BA", "LRCX", "AMT", "DE",
    "HCA", "CI", "FI", "BMY", "MDLZ", "GILD", "SO", "ICE", "SHW", "MO",
    "MCO", "DUK", "INTC", "CL", "WM", "ZTS", "SNPS", "APH", "GD", "CTAS",
    "TT", "EQIX", "PH", "CMG", "CME", "NOC", "CVS", "PYPL", "EOG", "ITW",
    "TDG", "AON", "TGT", "ABNB", "FDX", "WELL", "CDNS", "MSI", "MMM", "MCK",
    "USB", "PNC", "ECL", "BDX", "CSX", "CRWD", "RSG", "ORLY", "CARR", "FCX",
    "SLB", "NXPI", "MAR", "AJG", "DHI", "APD", "CEG", "AFL", "NEM", "EMR",
    "PSA", "TFC", "ROP", "MPC", "FTNT", "PSX", "ADSK", "WMB", "NSC", "GM",
    "SPG", "COF", "AZO", "O", "OXY", "HLT", "AEP", "MET", "SRE", "ROST",
    "OKE", "CPRT", "TRV", "CHTR", "LEN", "PCAR", "GEV", "BK", "URI", "DLR",
    "CCI", "KDP", "ALL", "KMB", "AIG", "JCI", "KMI", "D", "GWW", "PAYX",
    "TEL", "MNST", "VLO", "COR", "IQV", "MSCI", "MPWR", "STZ", "F", "FIS",
    "KHC", "RCL", "LHX", "AMP", "MCHP", "ODFL", "HUM", "CMI", "HES", "FICO",
    "PRU", "KVUE", "EW", "CNC", "ACGL", "PCG", "NDAQ", "A", "PEG", "IDXX",
    "PWR", "HWM", "HSY", "GIS", "EA", "AME", "FAST", "GEHC", "CTVA", "VRSK",
    "KR", "CTSH", "YUM", "EXC", "DOW", "SYY", "EXR", "OTIS", "EFX", "IT",
    "IR", "GLW", "NUE", "CBRE", "BKR", "FANG", "ED", "VICI", "HPQ", "GRMN",
    "XEL", "LULU", "EL", "DD", "MLM", "RMD", "VMC", "DFS", "IRM", "XYL",
    "HIG", "EIX", "SMCI", "ON", "CSGP", "LYB", "TRGP", "MRNA", "AVB", "CDW",
    "ROK", "MTD", "LVS", "BIIB", "PPG", "DXCM", "TSCO", "WEC", "BRO", "VST",
    "EBAY", "ADM", "WTW", "WAB", "FITB", "DVN", "NVR", "GPN", "TTWO", "HAL",
    "PHM", "MTB", "ANSS", "EQR", "K", "AWK", "DG", "VLTO", "AXON", "NTAP",
    "KEYS", "CAH", "DAL", "DTE", "IFF", "FTV", "FSLR", "ETR", "STT", "DOV",
    "FE", "CHD", "HPE", "VTR", "BR", "SBAC", "TYL", "TROW", "RJF", "ROL",
    "DECK", "ES", "SW", "PPL", "ZBH", "STE", "GDDY", "TSN", "WY", "CBOE",
    "WRB", "AEE", "STX", "LYV", "WST", "INVH", "TER", "BF.B", "WDC", "MKC",
    "ARE", "PTC", "HBAN", "CCL", "RF", "DLTR", "LDOS", "CINF", "CPAY", "HUBB",
    "BLDR", "MOH", "WBD", "ATO", "CMS", "WAT", "EQT", "GPC", "TDY", "BALL",
    "LH", "CFG", "OMC", "BAX", "APTV", "SYF", "BBY", "STLD", "CLX", "FOXA",
    "ESS", "COO", "J", "DRI", "HOLX", "PFG", "MAA", "PKG", "FOX", "ZBRA",
    "NTRS", "CTRA", "EXPE", "ULTA", "JBHT", "VRSN", "HRL", "L", "MAS", "AVY",
    "CNP", "SWKS", "NRG", "EXPD", "DGX", "ALGN", "EG", "IP", "TXT", "LUV",
    "ENPH", "GEN", "AMCR", "NWS", "MRO", "NWSA", "DOC", "KIM", "KEY", "FDS",
    "UHS", "SWK", "IEX", "AKAM", "CPB", "RVTY", "DPZ", "SNA", "LNT", "CAG",
    "CF", "NDSN", "NI", "CE", "PNR", "UDR", "BG", "UAL", "VTRS", "TRMB",
    "POOL", "EVRG", "KMX", "CPT", "DVA", "SJM", "REG", "PODD", "JNPR", "AES",
    "INCY", "JBL", "JKHY", "IPG", "HST", "AOS", "CHRW", "ALLE", "EMN", "BXP",
    "FFIV", "MGM", "TFX", "EPAM", "TECH", "LKQ", "TAP", "HII", "BEN", "CTLT",
    "QRVO", "RL", "APA", "CRL", "ALB", "SOLV", "AIZ", "MHK", "PNW", "FRT",
    "MTCH", "HAS", "GNRC", "TPR", "DAY", "GL", "MOS", "PAYC", "HSIC", "WBA",
    "LW", "MKTX", "BIO", "WYNN", "FMC", "CZR", "BWA", "BBWI", "IVZ", "NCLH",
    "PARA", "AAL", "ETSY"

]

list2 = [
    "KKR", "RHI", "CRWD", "CMA", "GDDY", "ILMN", "VST", "PXD", "XRAY", "VFC",
"GEV", "SOLV", "SMCI", "WHR", "DECK", "ZION", "UBER", "SEE", "JBL", "ALK",
"BLDR", "SEDG", "HUBB", "OGN", "LULU", "ATVI", "DXC", "VLTO", "BX", "LNC",
"ABNB", "NWL", "KVUE", "AAP", "PANW", "DISH", "AXON", "FRC", "FICO", "LUMN",
"BG", "SBNY", "PODD", "SIVB", "VNO", "GEHC", "STLD", "ABMD", "FSLR", "FBHS", "MBC", "AGCL", "TWTR", "TRGP", "NLSN", "PCG", "CTXS", "EQT", "DRE", "CSGP", "PVH", "PARA", "INVH", "PENN", "UA", "KDP", "UAA", "ON", "IPGP", "VICI", "CERN", "CPT", "PBCT", "MOH", "INFO", "NDSN", "XLNX", "GPS", "CEG", "SBNY", "ETSY", "ADS", "HOG", "TDY", "LEG", "SEDG", "HBI", "FDS", "WU", "EPAM", "KSU", "MTCH", "CDAY", "PRGO", "UNM", "BRO", "NOV", "TECH", "MXIM", "MRNA", "ALXN", "HFC", "OGN", "CRL", "FLIR", "PTC", "VAR", "NXPI", "FLS", "PENN", "SLG", "GNRC", "XRX", "CZR", "VNT", "MPWR", "FTI", "TRMB", "CXO", "ENPH", "TIF", "TSLA", "AIV", "NBL", "VNT", "POOL", "ETFC", "HRB", "TER", "COTY", "CTLT", "KSS", "BIO", "TYL", "JWN", "WST", "HP", "DPZ", "CPRI", "DXCM", "AGN", "M", "RTN", "OTIS", "CARR", "HWM", "ARNC", "IR", "XEC", "PAYC", "WCG", "LYV", "AMG", "ZBRA", "TRIP", "STE", "MAC", "ODFL", "STI", "WRB", "VIAB", "NOW", "CELG", "LVS", "NKTR", "NVR", "JEF", "CDW", "TSS", "LDOS", "APC", "IEX", "FL", "TMUS", "RHT", "MKTX", "LLL", "AMCR", "BMS", "MAT", "DD", "DWDP", "CTVA", "FLR"
]

# Convert list1 to a set for faster lookup
set_list1 = set(list1)

# Find unique elements in list2 that are not in list1
unique_in_list2 = [item for item in list2 if item not in set_list1]

# Print the total number of unique elements and the list itself
print(f"Total number of unique strings in list2: {len(unique_in_list2)}")
print("List of unique strings in list2:", unique_in_list2)
