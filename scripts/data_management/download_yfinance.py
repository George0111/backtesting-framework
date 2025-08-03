import yfinance as yf
# for s in ['SPY', 'AGG']:
#     df = yf.download(s, period='max', auto_adjust=True, multi_level_index=False)
#     # print(df.head())
#     df.to_csv(f'./data/{s}.csv')

universe = ['XL%s' % sector for sector in "BCEFIKPUVY"] + ['SPY']

universe = ['QQQ']

path = './data/'

for s in universe:
    df = yf.download(s, period='max', auto_adjust=False, multi_level_index=False)
    # print(df.head())
    df.to_csv(f'{path}{s}.csv')