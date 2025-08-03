import json
import pandas as pd

# Load JSON log
with open('./logs/twoETF_2025-05-12T23:12:48.815513.json', 'r') as f:
    log_events = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(log_events)

# Filter for relevant event type (e.g. 'next' or 'portfolio')
# Let's use 'portfolio' for total portfolio value and per-asset market value
df_portfolio = df[df['event'] == 'portfolio'].copy()

# Explode market_values dict into columns (one per asset)
market_values_df = df_portfolio['market_values'].apply(pd.Series)
market_values_df['datetime'] = df_portfolio['datetime']

# Melt for easy Plotly usage (long format: datetime, asset, value)
df_melted = market_values_df.melt(id_vars='datetime', var_name='asset', value_name='market_value')

# Convert datetime to pandas datetime for plotting
df_melted['datetime'] = pd.to_datetime(df_melted['datetime'])

import yfinance as yf

benchmark_ticker = '^GSPC'
benchmark = yf.download(
    benchmark_ticker,
    start=df_melted['datetime'].min().strftime('%Y-%m-%d'),
    end=df_melted['datetime'].max().strftime('%Y-%m-%d'),
    progress=False,
    multi_level_index=False
)
benchmark = benchmark[['Close']].reset_index()
benchmark = benchmark.rename(columns={'Date': 'datetime', 'Close': 'benchmark_value'})
benchmark['datetime'] = pd.to_datetime(benchmark['datetime'])

if isinstance(benchmark.index, pd.MultiIndex):
    benchmark = benchmark.reset_index()
    if 'Date' in benchmark.columns:
        benchmark = benchmark.rename(columns={'Date': 'datetime'})
    benchmark['datetime'] = pd.to_datetime(benchmark['datetime'])

# print(df_melted.head())
# print(benchmark.head())

# Now merge
df_compare = pd.merge_asof(
    df_melted.sort_values('datetime'),
    benchmark[['datetime', 'benchmark_value']].sort_values('datetime'),
    on='datetime',
    direction='backward'
)

print(df_compare.head())
# Optionally, normalize both series to start at 1 for comparison of relative performance
def normalize(series):
    return series / series.iloc[0]

df_compare['market_value_norm'] = df_compare.groupby('asset')['market_value'].transform(normalize)
df_compare['benchmark_value_norm'] = normalize(df_compare['benchmark_value'])

import plotly.graph_objs as go

assets = df_compare['asset'].dropna().unique()
traces = []
for i, asset in enumerate(assets):
    asset_df = df_compare[df_compare['asset'] == asset]
    # Portfolio value line (no markers)
    trace_asset = go.Scatter(
        x=asset_df['datetime'],
        y=asset_df['market_value_norm'],
        mode='lines',
        name=f'{asset} (Portfolio)',
        visible=(i == 0)
    )
    # Benchmark line (no markers)
    trace_bench = go.Scatter(
        x=asset_df['datetime'],
        y=asset_df['benchmark_value_norm'],
        mode='lines',
        name='Benchmark',
        line=dict(dash='dash', color='gray'),
        visible=(i == 0)
    )
    traces.extend([trace_asset, trace_bench])

# Dropdown buttons: show only corresponding asset+benchmark traces
buttons = []
for i, asset in enumerate(assets):
    vis = [False] * (2 * len(assets))
    vis[2*i] = True      # asset trace
    vis[2*i + 1] = True  # benchmark trace
    buttons.append(dict(
        label=asset,
        method='update',
        args=[{'visible': vis},
              {'title': f'Normalized Portfolio Value vs Benchmark: {asset}'}]
    ))

layout = go.Layout(
    title=f'Normalized Portfolio Value vs Benchmark: {assets[0]}',
    xaxis=dict(title='Datetime'),
    yaxis=dict(title='Normalized Value (Start=1)'),
    updatemenus=[dict(
        active=0,
        buttons=buttons,
        x=1.15,
        xanchor='right',
        y=1.15,
        yanchor='top'
    )]
)

fig = go.Figure(data=traces, layout=layout)
fig.write_html('portfolio_vs_benchmark_dropdown.html')
# fig.show()  # Uncomment if running in a Jupyter notebook
