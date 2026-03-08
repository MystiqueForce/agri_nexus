import pandas as pd

df = pd.read_csv("Agriculture_price_dataset.csv")

df.columns = df.columns.str.strip()

df = df.rename(columns={
    "STATE":"state",
    "District Name":"district",
    "Market Name":"market",
    "Commodity":"commodity",
    "Modal_Price":"price",
    "Price Date":"date"
})

df = df[
    ["state","district","market","commodity","price","date"]
]

df["date"] = pd.to_datetime(df["date"], errors="coerce")

df["price"] = pd.to_numeric(df["price"], errors="coerce")

df["commodity"] = df["commodity"].str.lower().str.strip()

df = df.dropna()

df.to_csv("prices_clean.csv", index=False)

print("Price dataset cleaned")