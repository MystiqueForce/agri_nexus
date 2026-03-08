import pandas as pd

market_df = pd.read_csv("market_data.csv")
weather_df = pd.read_csv("weather.csv")

market_df["date"] = pd.to_datetime(market_df["date"])
weather_df["date"] = pd.to_datetime(weather_df["date"])

df = market_df.merge(
    weather_df,
    on=["market","date"],
    how="left"
)

df = df.ffill()

df.to_csv("final_market_dataset.csv", index=False)

print("Weather merged")