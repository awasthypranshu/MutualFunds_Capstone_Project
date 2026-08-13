import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns

warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_theme(style='whitegrid')

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'Data' / 'Raw'
OUTPUT_DIR = ROOT / 'Report' / 'eda_charts'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

fund_master = pd.read_csv(DATA_DIR / '01_fund_master.csv', parse_dates=['launch_date'])
nav = pd.read_csv(DATA_DIR / '02_nav_history.csv', parse_dates=['date'])
aum = pd.read_csv(DATA_DIR / '03_aum_by_fund_house.csv', parse_dates=['date'])
sip = pd.read_csv(DATA_DIR / '04_monthly_sip_inflows.csv', parse_dates=['month'])
category_inflows = pd.read_csv(DATA_DIR / '05_category_inflows.csv', parse_dates=['month'])
folio = pd.read_csv(DATA_DIR / '06_industry_folio_count.csv', parse_dates=['month'])
scheme_perf = pd.read_csv(DATA_DIR / '07_scheme_performance.csv')
transactions = pd.read_csv(DATA_DIR / '08_investor_transactions.csv', parse_dates=['transaction_date'])
holdings = pd.read_csv(DATA_DIR / '09_portfolio_holdings.csv', parse_dates=['portfolio_date'])
bench = pd.read_csv(DATA_DIR / '10_benchmark_indices.csv', parse_dates=['date'])


def save_static(fig, name):
    path = OUTPUT_DIR / f'{name}.png'
    fig.savefig(path, dpi=300, bbox_inches='tight')
    return path


# 1. NAV trend analysis for all 40 schemes
nav_with_names = nav.merge(fund_master[['amfi_code', 'scheme_name']], on='amfi_code', how='left')
nav_plot = nav_with_names[(nav_with_names['date'].dt.year >= 2022) & (nav_with_names['date'].dt.year <= 2025)].copy()
nav_plot['date'] = pd.to_datetime(nav_plot['date']).dt.to_pydatetime()
fig1 = px.line(
    nav_plot,
    x='date',
    y='nav',
    color='scheme_name',
    title='Daily NAV trend for 40 mutual fund schemes (2022-2025)',
    labels={'date': 'Date', 'nav': 'NAV (₹)'}
)
fig1.add_vrect(x0='2023-01-01', x1='2023-12-31', fillcolor='green', opacity=0.08, line_width=0)
fig1.add_vrect(x0='2024-01-01', x1='2024-12-31', fillcolor='red', opacity=0.08, line_width=0)
fig1.add_annotation(x='2023-06-01', y=1.0, xref='x', yref='paper', text='2023 bull run', showarrow=False, font=dict(size=12))
fig1.add_annotation(x='2024-06-01', y=1.0, xref='x', yref='paper', text='2024 correction', showarrow=False, font=dict(size=12))
fig1.update_layout(showlegend=False, height=700, margin=dict(l=20, r=20, t=60, b=20))
fig1.write_image(OUTPUT_DIR / 'nav_trend_all_schemes.png', width=1600, height=900, scale=2)

# 2. AUM growth grouped bar by fund house
aum_year = aum.copy()
aum_year['year'] = aum_year['date'].dt.year
aum_year = aum_year.sort_values(['year', 'fund_house', 'date'])
aum_year = aum_year.groupby(['year', 'fund_house'], as_index=False).agg({'aum_crore': 'last', 'aum_lakh_crore': 'last'})
selected_houses = aum_year.groupby('fund_house')['aum_crore'].sum().sort_values(ascending=False).head(8).index.tolist()
aum_filtered = aum_year[aum_year['fund_house'].isin(selected_houses)]
pivot_aum = aum_filtered.pivot(index='year', columns='fund_house', values='aum_lakh_crore').fillna(0)
fig2, ax2 = plt.subplots(figsize=(14, 7))
pivot_aum.plot(kind='bar', ax=ax2, width=0.8, color=['#1f77b4' if h != 'SBI Mutual Fund' else '#d62728' for h in pivot_aum.columns])
ax2.set_title('AUM growth by fund house (2022-2025)', fontsize=14)
ax2.set_xlabel('Year')
ax2.set_ylabel('AUM (₹ Lakh Cr)')
ax2.legend(title=None)
for container in ax2.containers:
    for bar in container:
        if bar.get_width() > 0:
            pass
ax2.text(0.02, 0.98, 'SBI dominates the landscape', transform=ax2.transAxes, ha='left', va='top', fontsize=11, bbox=dict(facecolor='white', alpha=0.6))
save_static(fig2, 'aum_growth_by_fund_house')

# 3. SIP inflow time series
sip = sip.copy()
sip['month'] = pd.to_datetime(sip['month']).dt.to_pydatetime()
sip['year'] = pd.to_datetime(sip['month']).dt.year
fig3 = px.line(
    sip,
    x='month',
    y='sip_inflow_crore',
    markers=True,
    title='Monthly SIP inflows (Jan 2022 - Dec 2025)',
    labels={'month': 'Month', 'sip_inflow_crore': 'SIP inflow (₹ Cr)'}
)
max_row = sip.loc[sip['sip_inflow_crore'].idxmax()]
fig3.add_annotation(
    x=max_row['month'],
    y=max_row['sip_inflow_crore'],
    text=f"All-time high: ₹{max_row['sip_inflow_crore']:,.0f} Cr",
    showarrow=True,
    arrowhead=2,
    ax=0,
    ay=-40
)
fig3.update_layout(height=600, margin=dict(l=20, r=20, t=60, b=20))
fig3.write_image(OUTPUT_DIR / 'monthly_sip_inflows.png', width=1600, height=900, scale=2)

# 4. Category inflow heatmap
heatmap_data = category_inflows.pivot_table(index='category', columns='month', values='net_inflow_crore', aggfunc='sum').fillna(0)
heatmap_data = heatmap_data.sort_index(axis=1)
fig4, ax4 = plt.subplots(figsize=(16, 8))
sns.heatmap(heatmap_data, cmap='RdYlGn', linewidths=0.5, cbar_kws={'label': 'Net inflow (₹ Cr)'}, ax=ax4)
ax4.set_title('Category inflow heatmap by month', fontsize=14)
ax4.set_xlabel('Month')
ax4.set_ylabel('Fund category')
save_static(fig4, 'category_inflow_heatmap')

# 5. Investor age group pie chart
age_counts = transactions['age_group'].dropna().value_counts().sort_values(ascending=False)
fig5, ax5 = plt.subplots(figsize=(8, 8))
ax5.pie(age_counts.values, labels=age_counts.index, autopct='%1.1f%%', startangle=90, wedgeprops={'edgecolor': 'white'})
ax5.set_title('Investor age-group distribution')
save_static(fig5, 'investor_age_group_pie')

# 6. SIP amount box plot by age group
sip_txn = transactions[(transactions['transaction_type'] == 'SIP') & (transactions['amount_inr'] > 0)].copy()
fig6, ax6 = plt.subplots(figsize=(12, 6))
sns.boxplot(data=sip_txn, x='age_group', y='amount_inr', order=['18-25', '26-35', '36-45', '46-55', '56+'], ax=ax6)
ax6.set_title('SIP amount distribution by age group')
ax6.set_xlabel('Age group')
ax6.set_ylabel('SIP amount (₹)')
ax6.set_yscale('log')
save_static(fig6, 'sip_amount_boxplot_by_age')

# 7. Gender split
gender_counts = transactions['gender'].dropna().value_counts().sort_values(ascending=False)
fig7, ax7 = plt.subplots(figsize=(8, 6))
sns.barplot(x=gender_counts.index, y=gender_counts.values, palette='viridis', ax=ax7)
ax7.set_title('Investor gender split')
ax7.set_xlabel('Gender')
ax7.set_ylabel('Count')
save_static(fig7, 'gender_split_bar')

# 8. Geographic distribution by state
state_sip = transactions[(transactions['transaction_type'] == 'SIP') & (transactions['amount_inr'] > 0)].groupby('state')['amount_inr'].sum().sort_values(ascending=False).head(15)
state_sip = state_sip.sort_values(ascending=True)
fig8, ax8 = plt.subplots(figsize=(10, 7))
ax8.barh(state_sip.index, state_sip.values, color='#2ca02c')
ax8.set_title('Top 15 states by SIP amount')
ax8.set_xlabel('Total SIP amount (₹)')
ax8.set_ylabel('State')
save_static(fig8, 'sip_amount_by_state')

# 9. City tier split pie
city_tier = transactions[(transactions['transaction_type'] == 'SIP') & (transactions['city_tier'].notna())]['city_tier'].value_counts()
fig9, ax9 = plt.subplots(figsize=(8, 8))
ax9.pie(city_tier.values, labels=city_tier.index, autopct='%1.1f%%', startangle=90, wedgeprops={'edgecolor': 'white'})
ax9.set_title('T30 vs B30 city-tier split')
save_static(fig9, 'city_tier_split_pie')

# 10. Folio count growth line chart
fig10, ax10 = plt.subplots(figsize=(12, 6))
ax10.plot(folio['month'], folio['total_folios_crore'], marker='o', linewidth=2, color='#ff7f0e')
for milestone, label in [(folio['month'].iloc[0], 'Jan 2022'), (folio['month'].iloc[-1], 'Dec 2025')]:
    pass
ax10.set_title('Folio count growth (Jan 2022 to Dec 2025)')
ax10.set_xlabel('Month')
ax10.set_ylabel('Total folios (Cr)')
ax10.annotate('13.26 Cr', xy=(folio['month'].iloc[0], folio['total_folios_crore'].iloc[0]), xytext=(10, 10), textcoords='offset points')
ax10.annotate('26.12 Cr', xy=(folio['month'].iloc[-1], folio['total_folios_crore'].iloc[-1]), xytext=(10, -20), textcoords='offset points')
save_static(fig10, 'folio_count_growth')

# 11. NAV return correlation matrix
selected_scheme_ids = fund_master.head(10)['amfi_code'].tolist()
selected_nav = nav[nav['amfi_code'].isin(selected_scheme_ids)].merge(fund_master[['amfi_code', 'scheme_name']], on='amfi_code')
selected_pivot = selected_nav.pivot_table(index='date', columns='scheme_name', values='nav', aggfunc='last').sort_index()
selected_returns = selected_pivot.pct_change().dropna()
fig11, ax11 = plt.subplots(figsize=(12, 10))
correlation_matrix = selected_returns.corr()
sns.heatmap(correlation_matrix, annot=True, fmt='.2f', cmap='coolwarm', linewidths=0.5, ax=ax11)
ax11.set_title('Daily NAV return correlation matrix (10 selected funds)')
save_static(fig11, 'nav_return_correlation_heatmap')

# 12. Sector allocation donut
sector_weights = holdings.groupby('sector')['weight_pct'].sum().sort_values(ascending=False)
fig12, ax12 = plt.subplots(figsize=(8, 8))
ax12.pie(sector_weights.values, labels=sector_weights.index, autopct='%1.1f%%', startangle=90, wedgeprops={'width': 0.35})
ax12.set_title('Sector allocation across equity portfolios')
save_static(fig12, 'sector_allocation_donut')

# 13. Benchmark overlay
selected_scheme = fund_master[fund_master['scheme_name'].str.contains('SBI Bluechip', na=False)].iloc[0]
scheme_nav = nav[nav['amfi_code'] == selected_scheme['amfi_code']].copy()
scheme_nav['date'] = pd.to_datetime(scheme_nav['date']).dt.to_pydatetime()
benchmark_nav = bench[bench['index_name'] == 'NIFTY50'].copy()
benchmark_nav['date'] = pd.to_datetime(benchmark_nav['date']).dt.to_pydatetime()
fig13 = go.Figure()
fig13.add_trace(go.Scatter(x=scheme_nav['date'], y=scheme_nav['nav'], mode='lines', name=selected_scheme['scheme_name']))
fig13.add_trace(go.Scatter(x=benchmark_nav['date'], y=benchmark_nav['close_value'], mode='lines', name='NIFTY 50'))
fig13.update_layout(title='SBI Bluechip NAV vs NIFTY 50 benchmark', xaxis_title='Date', yaxis_title='Value', height=600)
fig13.write_image(OUTPUT_DIR / 'benchmark_overlay.png', width=1600, height=900, scale=2)

# 14. Scheme performance scatter
fig14, ax14 = plt.subplots(figsize=(10, 7))
scatter = ax14.scatter(
    scheme_perf['std_dev_ann_pct'],
    scheme_perf['return_5yr_pct'],
    s=np.array(scheme_perf['aum_crore']) / 1000,
    c=scheme_perf['morningstar_rating'],
    cmap='viridis',
    alpha=0.8
)
for _, row in scheme_perf.head(10).iterrows():
    ax14.text(row['std_dev_ann_pct'] + 0.2, row['return_5yr_pct'] + 0.2, row['scheme_name'][:15], fontsize=8)
ax14.set_title('5-year returns vs volatility by scheme')
ax14.set_xlabel('Annualized volatility (%)')
ax14.set_ylabel('5-year return (%)')
fig14.colorbar(scatter, ax=ax14, label='Morningstar rating')
save_static(fig14, 'scheme_return_volatility_scatter')

# 15. Active SIP accounts trend
fig15 = px.line(
    sip,
    x='month',
    y='active_sip_accounts_crore',
    markers=True,
    title='Active SIP accounts (2022-2025)',
    labels={'month': 'Month', 'active_sip_accounts_crore': 'Active SIP accounts (Cr)'}
)
fig15.update_layout(height=600, margin=dict(l=20, r=20, t=60, b=20))
fig15.write_image(OUTPUT_DIR / 'active_sip_accounts.png', width=1600, height=900, scale=2)

print('EDA charts exported to', OUTPUT_DIR)
