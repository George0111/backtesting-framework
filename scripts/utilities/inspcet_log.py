import pandas as pd
import json

logname = 'twoETF'
# Convert log file to DataFrame
with open(f"./logs/{logname}/orders_and_trades_{logname}.log", "r") as log_file:
    log_entries = [json.loads(line) for line in log_file]
with open(f"./logs/{logname}/next_events_{logname}.log", "r") as log_file:
    next_log_entries = [json.loads(line) for line in log_file]
# Separate trades and orders
trades = [entry for entry in log_entries if entry['event'] == 'trade']
orders = [entry for entry in log_entries if entry['event'] == 'order']

trades_df = pd.DataFrame(trades)
orders_df = pd.DataFrame(orders)

print("Trades DataFrame:")
print(trades_df)
trades_df.to_csv(f"./inspect/trades_{logname}.csv", index=False)
print("\nOrders DataFrame:")
print(orders_df)
orders_df.to_csv(f"./inspect/orders_{logname}.csv", index=False)



# Separate trades and orders
nexts = [entry for entry in next_log_entries if entry['event'] == 'next']
track_orders = [entry for entry in next_log_entries if entry['event'] == 'track_order']
portfolios = [entry for entry in next_log_entries if entry['event'] == 'portfolio']

nexts = pd.DataFrame(nexts)
track_orders = pd.DataFrame(track_orders)
portfolios = pd.DataFrame(portfolios)

print("\nNexts DataFrame:")
print(nexts)
nexts.to_csv(f"./inspect/nexts_{logname}.csv", index=False)
print("\nTrack Orders DataFrame:")
print(track_orders)
track_orders.to_csv(f"./inspect/track_orders_{logname}.csv", index=False)    
print("\nPortfolios DataFrame:")
print(portfolios)
portfolios.to_csv(f"./inspect/portfolios_{logname}.csv", index=False)