import requests
import pandas as pd
from datetime import datetime

mandis = pd.read_csv("mandis.csv")

start = "20230101"
end = "20250301"

weather_data = []

for _, row in mandis.iterrows():

    lat = row["lat"]
    lon = row["lon"]
    market = row["market"]

    url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR&community=AG&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON"

    r = requests.get(url).json()

    temp = r["properties"]["parameter"]["T2M"]
    rain = r["properties"]["parameter"]["PRECTOTCORR"]

    for d in temp:

        weather_data.append({
            "market": market,
            "date": datetime.strptime(d,"%Y%m%d"),
            "temperature": temp[d],
            "rainfall": rain[d]
        })

weather_df = pd.DataFrame(weather_data)

weather_df.to_csv("weather.csv", index=False)

print("Weather dataset ready")