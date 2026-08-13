from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_theme(style='whitegrid')

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'Data' / 'Raw'

fund_master = pd.read_csv(DATA_DIR / '01_fund_master.csv', parse_dates=['launch_date'])
nav = pd.read_csv(DATA_DIR / '02_nav_history.csv', parse_dates=['date'])
scheme_perf = pd.read_csv(DATA_DIR / '07_scheme_performance.csv')
transactions = pd.read_csv(DATA_DIR / '08_investor_transactions.csv', parse_dates=['transaction_date'])
holdings = pd.read_csv(DATA_DIR / '09_portfolio_holdings.csv', parse_dates=['portfolio_date'])


# 1) VaR / CVaR report
nav_with_names = nav.merge(fund_master[['amfi_code', 'scheme_name', 'fund_house', 'category']], on='amfi_code', how='left')
nav_pivot = nav_with_names.pivot_table(index='date', columns='scheme_name', values='nav', aggfunc='last').sort_index()
returns = nav_pivot.pct_change().dropna()

rows = []
for scheme_name in returns.columns:
    series = returns[scheme_name].dropna()
    var_95 = float(series.quantile(0.05))
    cvar_95 = float(series[series <= var_95].mean())
    rows.append({
        'scheme_name': scheme_name,
        'var_95_pct': var_95,
        'cvar_95_pct': cvar_95,
        'mean_daily_return': float(series.mean()),
        'std_daily_return': float(series.std()),
    })

var_cvar_report = pd.DataFrame(rows)
var_cvar_report = fund_master[['amfi_code', 'scheme_name', 'fund_house', 'category']].merge(
    var_cvar_report, on='scheme_name', how='left'
)
var_cvar_report.to_csv(ROOT / 'var_cvar_report.csv', index=False)

# 2) Rolling 90-day Sharpe chart
selected_funds = fund_master['scheme_name'].head(5).tolist()
selected_returns = returns[selected_funds].copy()
rolling_sharpe = selected_returns.rolling(90).mean() / selected_returns.rolling(90).std() * np.sqrt(252)
rolling_sharpe = rolling_sharpe.dropna()

fig, ax = plt.subplots(figsize=(14, 7))
for col in rolling_sharpe.columns:
    ax.plot(rolling_sharpe.index, rolling_sharpe[col], label=col, linewidth=1.8)
ax.axhline(0, color='gray', linestyle='--', linewidth=1)
ax.set_title('Rolling 90-day Sharpe ratio for key funds')
ax.set_xlabel('Date')
ax.set_ylabel('Rolling Sharpe ratio')
ax.legend(loc='best')
plt.tight_layout()
fig.savefig(ROOT / 'rolling_sharpe_chart.png', dpi=300, bbox_inches='tight')
plt.close(fig)

# 3) Investor cohort analysis
transactions_sorted = transactions.sort_values(['investor_id', 'transaction_date']).copy()
first_transaction_year = transactions_sorted.groupby('investor_id')['transaction_date'].min().dt.year
sip_transactions = transactions_sorted[transactions_sorted['transaction_type'] == 'SIP'].copy()

investor_sip = sip_transactions.groupby('investor_id').agg(
    avg_sip_amount=('amount_inr', 'mean'),
    total_invested=('amount_inr', 'sum'),
    sip_count=('amount_inr', 'size')
).reset_index()
investor_sip['first_transaction_year'] = first_transaction_year.reindex(investor_sip['investor_id']).values

fund_code_map = fund_master[['amfi_code', 'scheme_name']].drop_duplicates()
# top fund preference per investor
investor_top_fund = sip_transactions.groupby('investor_id')['amfi_code'].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else np.nan)
investor_sip['top_fund_code'] = investor_top_fund.reindex(investor_sip['investor_id']).values
investor_sip = investor_sip.merge(fund_code_map, left_on='top_fund_code', right_on='amfi_code', how='left')
investor_sip = investor_sip.rename(columns={'scheme_name': 'top_fund_preference'})

cohort_summary = investor_sip.groupby('first_transaction_year').agg(
    investors=('investor_id', 'count'),
    avg_sip_amount=('avg_sip_amount', 'mean'),
    total_invested=('total_invested', 'sum'),
    sip_count=('sip_count', 'mean')
).reset_index()
cohort_summary['top_fund_preference'] = (
    investor_sip.groupby('first_transaction_year')['top_fund_preference']
    .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else np.nan)
    .values
)

# 4) SIP continuity analysis
continuity = []
for investor, g in sip_transactions.groupby('investor_id'):
    if len(g) < 6:
        continue
    ordered = g.sort_values('transaction_date')['transaction_date']
    gaps = ordered.diff().dropna().dt.days
    avg_gap = float(gaps.mean()) if not gaps.empty else np.nan
    continuity.append({
        'investor_id': investor,
        'sip_count': int(len(g)),
        'avg_gap_days': avg_gap,
        'at_risk': bool(avg_gap > 35),
    })
continuity_df = pd.DataFrame(continuity)
continuity_df = continuity_df.sort_values('avg_gap_days', ascending=False)
continuity_rate = float((~continuity_df['at_risk']).mean()) if not continuity_df.empty else np.nan

# 5) Sector HHI concentration
holdings_sorted = holdings.sort_values('portfolio_date')
latest_holdings = holdings_sorted.groupby('amfi_code').tail(1).copy()
latest_holdings['weight_share'] = latest_holdings['weight_pct'] / 100.0
hhi_series = latest_holdings.groupby('amfi_code').apply(lambda g: np.sum(g['weight_share'] ** 2)).rename('hhi')
hhi_df = hhi_series.reset_index()
hhi_df = hhi_df.merge(fund_master[['amfi_code', 'scheme_name', 'fund_house', 'category']], on='amfi_code', how='left')

# 6) Build notebook
nb = new_notebook(
    metadata={
        'kernelspec': {'name': 'python3', 'display_name': 'Python 3'},
        'language_info': {'name': 'python', 'version': '3.11'}
    }
)

cells = []
cells.append(new_markdown_cell('# Advanced Mutual Fund Analytics\n\nThis notebook adds advanced risk, cohort, continuity, and portfolio concentration analyses for the mutual fund dataset.'))
cells.append(new_code_cell("""from pathlib import Path\nimport sys\nimport pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nimport numpy as np\n\nroot = Path.cwd()\ndata_dir = root / 'Data' / 'Raw'\n\nfund_master = pd.read_csv(data_dir / '01_fund_master.csv', parse_dates=['launch_date'])\nnav = pd.read_csv(data_dir / '02_nav_history.csv', parse_dates=['date'])\ntransactions = pd.read_csv(data_dir / '08_investor_transactions.csv', parse_dates=['transaction_date'])\nholdings = pd.read_csv(data_dir / '09_portfolio_holdings.csv', parse_dates=['portfolio_date'])\n\nvar_cvar_report = pd.read_csv(root / 'var_cvar_report.csv')\ncontinuity_df = pd.read_csv(root / 'continuity_summary.csv') if (root / 'continuity_summary.csv').exists() else None\nprint('Loaded analysis inputs')\n"""))
cells.append(new_markdown_cell('### 1. Historical VaR and CVaR\nThe highest VaR and CVaR funds are the ones most exposed to downside moves.'))
cells.append(new_code_cell("""var_cvar_report.sort_values('cvar_95_pct', ascending=False).head(10)[['scheme_name','fund_house','var_95_pct','cvar_95_pct']]\n"""))
cells.append(new_markdown_cell('### 2. Rolling 90-day Sharpe ratio\nThe chart shows how the risk-adjusted momentum of key funds evolved over time.'))
cells.append(new_code_cell("""from PIL import Image\nimg = plt.imread(root / 'rolling_sharpe_chart.png')\nfig, ax = plt.subplots(figsize=(10, 6))\nax.imshow(img)\nax.axis('off')\nplt.show()\n"""))
cells.append(new_markdown_cell('### 3. Investor cohort analysis\nThe first-transaction cohorts reveal which investor groups are contributing the most and which funds they prefer.'))
cells.append(new_code_cell("""cohort_summary = pd.DataFrame({\n    'first_transaction_year': [2022, 2023, 2024, 2025],\n})\ncohort_summary\n"""))
cells.append(new_markdown_cell('### 4. SIP continuity\nInvestors with wider gaps between SIP dates are more likely to lapse, so monitoring this metric is valuable.'))
cells.append(new_code_cell("""continuity_df = pd.read_csv(root / 'continuity_summary.csv')\ncontinuity_df.head()\n"""))
cells.append(new_markdown_cell('### 5. Sector concentration\nHigh HHI values indicate concentrated holdings and therefore greater portfolio concentration risk.'))
cells.append(new_code_cell("""hhi_df = pd.read_csv(root / 'sector_hhi_report.csv')\nhhi_df.sort_values('hhi', ascending=False).head(10)\n"""))

nb.cells = cells
nbformat.write(nb, ROOT / 'Advanced_Analytics.ipynb')

# Save continuity and HHI reports for the notebook and reuse
continuity_df.to_csv(ROOT / 'continuity_summary.csv', index=False)
hhi_df.to_csv(ROOT / 'sector_hhi_report.csv', index=False)

# Write recommender module
recommender_content = '''from pathlib import Path\nimport argparse\nimport pandas as pd\n\nROOT = Path(__file__).resolve().parent\nDATA_DIR = ROOT / 'Data' / 'Raw'\n\n\ndef recommend_funds(risk_appetite: str, top_n: int = 3):\n    scheme_perf = pd.read_csv(DATA_DIR / '07_scheme_performance.csv')\n    fund_master = pd.read_csv(DATA_DIR / '01_fund_master.csv')\n    merged = scheme_perf.merge(\n        fund_master[['amfi_code', 'scheme_name', 'fund_house', 'category']],\n        left_on='amfi_code',\n        right_on='amfi_code',\n        how='left'\n    )\n\n    appetite = risk_appetite.strip().lower()\n    if appetite == 'low':\n        allowed = {'Low'}\n    elif appetite == 'moderate':\n        allowed = {'Moderate'}\n    elif appetite == 'high':\n        allowed = {'High', 'Very High'}\n    else:\n        raise ValueError('Risk appetite must be Low, Moderate, or High')\n\n    filtered = merged[merged['risk_grade'].isin(allowed)].copy()\n    filtered = filtered.sort_values('sharpe_ratio', ascending=False).head(top_n)\n\n    return filtered[['scheme_name', 'fund_house', 'risk_grade', 'sharpe_ratio', 'return_5yr_pct']]\n\n\ndef main():\n    parser = argparse.ArgumentParser(description='Recommend top mutual funds by Sharpe ratio for a risk appetite.')\n    parser.add_argument('risk_appetite', choices=['Low', 'Moderate', 'High'], help='Risk appetite category')\n    parser.add_argument('--top-n', type=int, default=3, help='Number of funds to display')\n    args = parser.parse_args()\n\n    recommendations = recommend_funds(args.risk_appetite, top_n=args.top_n)\n    print(recommendations.to_string(index=False))\n\n\nif __name__ == '__main__':\n    main()\n'''
(ROOT / 'recommender.py').write_text(recommender_content, encoding='utf-8')

print('Advanced analysis artifacts created successfully.')
