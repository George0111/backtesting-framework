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

import plotly.graph_objs as go

# Get unique assets
assets = df_melted['asset'].dropna().unique()

# Create one trace per asset (hidden by default, except the first)
traces = []
for i, asset in enumerate(assets):
    asset_df = df_melted[df_melted['asset'] == asset]
    trace = go.Scatter(
        x=asset_df['datetime'],
        y=asset_df['market_value'],
        mode='lines+markers',
        name=asset,
        visible=(i == 0)  # Only the first asset is visible at start
    )
    traces.append(trace)

# Create dropdown buttons
buttons = []
for i, asset in enumerate(assets):
    # Only show the i-th trace
    visibility = [False] * len(assets)
    visibility[i] = True
    button = dict(
        label=asset,
        method='update',
        args=[{'visible': visibility},
              {'title': f'Portfolio Holding Value: {asset}'}]
    )
    buttons.append(button)

# Create layout with dropdown
layout = go.Layout(
    title=f'Portfolio Holding Value: {assets[0]}',
    xaxis=dict(title='Datetime'),
    yaxis=dict(title='Market Value'),
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

# Save to HTML
fig.write_html('portfolio_holdings_dropdown.html')

# Or display in notebook (if using Jupyter)
# fig.show()
