import pandas as pd

price_df = pd.read_csv("prices_clean.csv")
arrival_df = pd.read_csv("arrival_data/arrivals_all.csv")

price_df["date"] = pd.to_datetime(price_df["date"])
arrival_df["date"] = pd.to_datetime(arrival_df["date"])

df = price_df.merge(
    arrival_df,
    on=["date","state","district","market","commodity"],
    how="left"
)

df["arrivals"] = df["arrivals"].fillna(0)

df.to_csv("market_data.csv", index=False)

print("Price + Arrival merged")