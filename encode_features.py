import pandas as pd
from sklearn.preprocessing import LabelEncoder
import pickle
import os

# create models directory if missing
os.makedirs("models", exist_ok=True)

df = pd.read_csv("features_dataset.csv")

market_encoder = LabelEncoder()
crop_encoder = LabelEncoder()

df["market_id"] = market_encoder.fit_transform(df["market"])
df["crop_id"] = crop_encoder.fit_transform(df["commodity"])

pickle.dump(market_encoder, open("models/market_encoder.pkl","wb"))
pickle.dump(crop_encoder, open("models/crop_encoder.pkl","wb"))

df.to_csv("model_dataset.csv", index=False)

print("Encoding complete")