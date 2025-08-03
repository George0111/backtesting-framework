import pandas as pd
import ast # Import ast to safely evaluate string representations of dictionaries
import matplotlib.pyplot as plt
import numpy as np

initial_capital = 10000
df = pd.read_csv("./pnl_TAA.csv", index_col=0, parse_dates=True)

df.replace(0, np.nan, inplace=True)  # Replace 0 with NaN
df = df.diff(1).fillna(0)
pnl_curve = df.cumsum()  # Cumulative sum to get the equity curve
# equity_curve.to_csv("./equity_curve_TAA.csv")
print(pnl_curve.tail().sum(axis=1))
pnl_curve.plot(title="PnL Curve", figsize=(12, 6))
plt.xlabel("Date")
plt.ylabel("PnL")
plt.grid()
plt.show()