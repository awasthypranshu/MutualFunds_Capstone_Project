from pathlib import Path
import argparse
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'Data' / 'Raw'


def recommend_funds(risk_appetite: str, top_n: int = 3):
    scheme_perf = pd.read_csv(DATA_DIR / '07_scheme_performance.csv')
    fund_master = pd.read_csv(DATA_DIR / '01_fund_master.csv')
    merged = scheme_perf.merge(
        fund_master[['amfi_code', 'scheme_name', 'fund_house', 'category']],
        left_on='amfi_code',
        right_on='amfi_code',
        how='left'
    )

    appetite = risk_appetite.strip().lower()
    if appetite == 'low':
        allowed = {'Low'}
    elif appetite == 'moderate':
        allowed = {'Moderate'}
    elif appetite == 'high':
        allowed = {'High', 'Very High'}
    else:
        raise ValueError('Risk appetite must be Low, Moderate, or High')

    filtered = merged[merged['risk_grade'].isin(allowed)].copy()
    filtered = filtered.sort_values('sharpe_ratio', ascending=False).head(top_n)

    return filtered[['scheme_name', 'fund_house', 'risk_grade', 'sharpe_ratio', 'return_5yr_pct']]


def main():
    parser = argparse.ArgumentParser(description='Recommend top mutual funds by Sharpe ratio for a risk appetite.')
    parser.add_argument('risk_appetite', choices=['Low', 'Moderate', 'High'], help='Risk appetite category')
    parser.add_argument('--top-n', type=int, default=3, help='Number of funds to display')
    args = parser.parse_args()

    recommendations = recommend_funds(args.risk_appetite, top_n=args.top_n)
    print(recommendations.to_string(index=False))


if __name__ == '__main__':
    main()
