import pandas as pd

df = pd.read_csv("final_market_dataset_fixed.csv")

# Fix date parsing
df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

df = df.dropna(subset=["date"])

# Sort for time series
df = df.sort_values(["market","commodity","date"])

# Time features
df["day_of_week"] = df["date"].dt.dayofweek
df["month"] = df["date"].dt.month


# PRICE LAGS
df["price_lag1"] = df.groupby(["market","commodity"])["price"].shift(1)
df["price_lag7"] = df.groupby(["market","commodity"])["price"].shift(7)


# ARRIVAL LAGS
df["arrival_lag1"] = df.groupby(["market","commodity"])["arrivals"].shift(1)
df["arrival_lag7"] = df.groupby(["market","commodity"])["arrivals"].shift(7)


# Rolling averages (SAFE METHOD)
df["rolling_price_7"] = df.groupby(
    ["market","commodity"]
)["price"].transform(lambda x: x.rolling(7).mean())

df["rolling_arrival_7"] = df.groupby(
    ["market","commodity"]
)["arrivals"].transform(lambda x: x.rolling(7).mean())


# Drop rows where lag values don't exist
df = df.dropna()

df.to_csv("features_dataset.csv", index=False)

print("Feature dataset created")
print(df.shape)