import pandas as pd
import lightgbm as lgb
import pickle

df = pd.read_csv("model_dataset.csv")

price_features = [
    "market_id",
    "crop_id",
    "arrival_lag7",
    "price_lag1",
    "price_lag7",
    "rolling_price_7",
    "temperature",
    "rainfall",
    "day_of_week",
    "month"
]

arrival_features = [
    "market_id",
    "crop_id",
    "arrival_lag1",
    "arrival_lag7",
    "rolling_arrival_7",
    "price_lag1",
    "temperature",
    "rainfall",
    "day_of_week",
    "month"
]

price_model = lgb.LGBMRegressor(
    n_estimators=800,
    learning_rate=0.05,
    max_depth=8
)

arrival_model = lgb.LGBMRegressor(
    n_estimators=800,
    learning_rate=0.05,
    max_depth=8
)

# Train models
price_model.fit(df[price_features], df["price"])
arrival_model.fit(df[arrival_features], df["arrivals"])

# Save models
pickle.dump(price_model, open("models/price_model.pkl","wb"))
pickle.dump(arrival_model, open("models/arrival_model.pkl","wb"))

print("Models trained and saved")