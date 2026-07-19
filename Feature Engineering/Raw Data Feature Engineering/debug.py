# from loaders import load_raw

# df = load_raw("../data/monitoring_data(raw).csv")

# print(df.dtypes)
# print()

# dups = df.duplicated(
#     subset=["factory_id", "timestamp", "parameter_id"],
#     keep=False
# )

# print("Duplicate rows after load_raw():", dups.sum())

# if dups.any():
#     print(df.loc[dups].sort_values(
#         ["factory_id", "timestamp", "parameter_id"]
#     ).head(20))


#----- Looking at timestamp values

# from loaders import load_raw
# import pandas as pd

# raw = pd.read_csv("../data/monitoring_data(raw).csv")

# print(raw["timestamp"].head(20))


# import pandas as pd

# raw = pd.read_csv("../data/monitoring_data(raw).csv")

# parsed = pd.to_datetime(
#     raw["timestamp"],
#     errors="coerce"
# )

# bad = raw.loc[parsed.isna(), ["timestamp", "factory_id", "parameter_id"]]

# print("Bad timestamps:", len(bad))
# print()
# print(bad.head(50))

from loaders import load_raw

df = load_raw("../data/monitoring_data(raw).csv")

print("NaT timestamps:", df["timestamp"].isna().sum())
print(df[df["timestamp"].isna()].head())