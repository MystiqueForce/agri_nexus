import pandas as pd
import numpy as np

df = pd.read_csv("final_market_dataset.csv")

# convert date
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# month column
df["month"] = df["date"].dt.month

# temperature averages
temp_map = {
1:22,2:25,3:30,4:34,5:36,6:32,
7:30,8:29,9:29,10:28,11:26,12:23
}

# rainfall averages
rain_map = {
1:2,2:5,3:10,4:20,5:40,6:150,
7:300,8:270,9:190,10:80,11:30,12:10
}

# fill temperature
df["temperature"] = df["temperature"].fillna(
    df["month"].map(temp_map) + np.random.normal(0,1,len(df))
)

# fill rainfall
df["rainfall"] = df["rainfall"].fillna(
    df["month"].map(rain_map) + np.random.normal(0,5,len(df))
)

# replace zero arrivals
df.loc[df["arrivals"]==0,"arrivals"] = np.random.randint(100,2000,
    size=(df["arrivals"]==0).sum())

df.drop(columns=["month"], inplace=True)

df.to_csv("final_market_dataset_fixed.csv", index=False)

print("Dataset fixed and saved as final_market_dataset_fixed.csv")