# Bluestock Mutual Fund Analytics Dashboard

A working, interactive analytics dashboard built to the same spec as the Power BI
brief — 4 pages, KPI cards, slicers, drill-through, dual-axis and heatmap charts.
Built as a **Streamlit + Plotly** app instead of a `.pbix` file (see note below).

## Why not an actual `.pbix`?

Power BI Desktop is a Windows GUI application. This environment is a headless Linux
sandbox with no GUI and no Power BI install, so there's no way to author or export a
real `.pbix`, PDF, or page-PNG from here. If that exact deliverable is a hard
requirement (e.g. for a course submission), you'll need to either:

1. Take this app's chart logic and rebuild it in Power BI Desktop on your own
   machine (the data model, relationships, and every chart's fields are all
   spelled out in `app.py`, so it's a fairly mechanical port), or
2. Submit this app instead if the format is flexible — it does everything the
   spec asked for (KPIs, slicers, scatter/bubble, dual-axis, heatmap,
   drill-through) and is arguably faster to iterate on than Power BI.

## How to run it

### Option 1: Using the existing virtual environment (Recommended)
```powershell
.\env\Scripts\python.exe -m streamlit run app.py
```

### Option 2: Active environment / Standard terminal
```bash
streamlit run app.py
```

It opens in your browser at `http://localhost:8501`.


## What's inside

- **Page 1 · Industry Overview** — KPI cards (computed live from the data, not
  hardcoded) + industry AUM trend + AUM by AMC bar chart.
- **Page 2 · Fund Performance** — risk/return bubble chart (bubble size = AUM),
  sortable scorecard, fund-house/category/plan slicers, and a drill-through
  selector that plots any scheme's NAV against a rebased NIFTY 50 benchmark.
- **Page 3 · Investor Analytics** — transaction amount by state, SIP/Lumpsum/
  Redemption donut, average SIP by age group, monthly transaction volume, with
  state/age/city-tier slicers.
- **Page 4 · SIP & Market Trends** — dual-axis SIP inflow vs NIFTY 50, category
  inflow heatmap, top-5 categories by FY25 net inflow.
- Bluestock-style blue/gold theme applied via CSS + a shared Plotly color
  sequence — swap the hex codes at the top of `app.py` for the real brand kit,
  and drop a logo image into the sidebar with `st.sidebar.image(...)`.

## Data notes worth knowing

- This dataset covers **40 schemes across 10 AMCs** — it's a synthetic subset,
  not the full Indian MF industry. Two of your spec's KPI numbers matched this
  data exactly (₹31K Cr SIP inflows, 26.12 Cr folios); two didn't (total AUM
  computes to ₹62.7L Cr here, not ₹81L Cr; scheme count is 40, not 1,908). The
  dashboard shows the real computed numbers rather than the spec's hardcoded
  ones — worth checking which is correct for your submission.
- `08_investor_transactions.csv` only covers Jan 2024–May 2025, narrower than
  the 2022–2025 range of the other tables — Page 3's charts will look sparser
  than Pages 1 and 4.
- Benchmark matching on Page 2 falls back to NIFTY50 for every scheme since
  `10_benchmark_indices.csv` only contains that one index, even though
  `01_fund_master.csv` lists a few different benchmark names.

## What to extend first

1. **PDF/PNG export** — add a "Download report" button using `plotly`'s
   `fig.write_image()` (needs `kaleido`) to snapshot each page, or run the app
   headless with `streamlit-shot`/`playwright` to capture full-page PNGs — the
   closest analog to the spec's export requirement.
2. **Real drill-through UX** — right now Page 2's drill-through is a selectbox;
   swapping it for `st.dataframe(..., on_select="rerun")` (Streamlit ≥1.35) lets
   you click a table row directly and jump to that scheme's NAV chart, closer to
   Power BI's native drill-through gesture.
3. **Category/sector filters on Page 4** and a **fund-house filter on Page 1**
   — those two pages are currently unfiltered; the slicer pattern from Pages 2
   and 3 drops in directly.
4. **Caching + incremental refresh** — `@st.cache_data` currently reloads
   everything if any CSV changes; for a growing dataset, switch to loading into
   SQLite (matches your original ODBC plan) and query with `pd.read_sql`.
5. **Logo + exact brand colors** — the theme block at the top of `app.py` is a
   placeholder; swap in the real Bluestock hex codes and logo file once you
   have them.
