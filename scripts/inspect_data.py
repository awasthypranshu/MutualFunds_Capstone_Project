import pandas as pd
from pathlib import Path
base = Path(r'c:/Users/awast/OneDrive/Desktop/Capstone Project/Data/Raw')
files = ['01_fund_master.csv','02_nav_history.csv','03_aum_by_fund_house.csv','04_monthly_sip_inflows.csv','05_category_inflows.csv','06_industry_folio_count.csv','07_scheme_performance.csv','08_investor_transactions.csv','09_portfolio_holdings.csv','10_benchmark_indices.csv']
for name in files:
    p = base / name
    print('\n===', name, '===')
    if p.exists():
        df = pd.read_csv(p)
        print(df.head(3).to_string())
        print('\ncolumns:', list(df.columns))
        print('shape:', df.shape)
    else:
        print('MISSING')
