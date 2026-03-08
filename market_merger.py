import pandas as pd
import glob

files = glob.glob("arrival_data/*.csv")

dfs = []

for file in files:

    df = pd.read_csv(file)

    # clean column names
    df.columns = df.columns.str.strip().str.lower()

    # rename columns
    df = df.rename(columns={
        "state": "state",
        "district": "district",
        "market": "market",
        "commodity": "commodity",
        "arrival quantity": "arrivals",
        "arrival date": "date"
    })

    # check columns
    print("Columns in file:", df.columns)

    # select only required columns
    df = df[
        ["state","district","market","commodity","arrivals","date"]
    ]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["arrivals"] = pd.to_numeric(df["arrivals"], errors="coerce")

    dfs.append(df)

arrival_df = pd.concat(dfs, ignore_index=True)

arrival_df = arrival_df.dropna()

arrival_df["commodity"] = arrival_df["commodity"].str.lower().str.strip()

arrival_df.to_csv("arrival_data/arrivals_all.csv", index=False)

print("Arrival dataset created")