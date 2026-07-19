import os
import json
import pandas as pd


def main():

    parquet_path = "../output/real_features.parquet"

    # If script is executed from project root
    if (
        not os.path.exists(parquet_path)
        and os.path.exists("output/real_features.parquet")
    ):
        parquet_path = "output/real_features.parquet"

    if not os.path.exists(parquet_path):
        raise FileNotFoundError(
            f"Feature matrix not found:\n{parquet_path}\n"
            "Run run_raw.py first."
        )

    print(f"\nReading feature matrix:\n{parquet_path}")

    df = pd.read_parquet(parquet_path)

    schema = {
        column: str(dtype)
        for column, dtype in df.dtypes.items()
    }

    save_path = os.path.join(
        os.path.dirname(__file__),
        "schema.json"
    )

    with open(save_path, "w") as f:
        json.dump(schema, f, indent=4)

    print("\nSchema successfully generated.\n")

    print("Columns")

    for col, dtype in schema.items():
        print(f"  {col:<35} {dtype}")

    print(f"\nSaved to:\n{save_path}")


if __name__ == "__main__":
    main()