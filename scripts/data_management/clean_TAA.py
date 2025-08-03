import pandas as pd

df = pd.read_csv(f'./TAA/SPY.csv', index_col=0, parse_dates=True)
common_index = df.index

for s in ['XL%s' % sector for sector in "BCEFIKPUVY"]+['SPY']:
    df = pd.read_csv(f'./TAA/{s}.csv', index_col=0, parse_dates=True)
    aligned_df = df.reindex(common_index).fillna(0)
    aligned_df.to_csv(f'./TAA/{s}.csv')
