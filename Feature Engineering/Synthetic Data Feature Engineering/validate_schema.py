import os
import json
import pandas as pd

def main():
    # Resolve parquet path
    parquet_path = '../../Data/SynData/synthetic_features.parquet'
    if not os.path.exists(parquet_path) and os.path.exists('Data/SynData/synthetic_features.parquet'):
        parquet_path = 'Data/SynData/synthetic_features.parquet'
    elif not os.path.exists(parquet_path) and os.path.exists('../output/synthetic_features.parquet'):
        parquet_path = '../output/synthetic_features.parquet'
        
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Parquet file not found at {parquet_path}. Run run_synthetic.py first.")
        
    print(f"Reading schema from: {parquet_path}")
    df = pd.read_parquet(parquet_path)
    
    # Extract columns and dtypes as strings
    schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
    
    # Determine save path (local directory)
    save_path = os.path.join(os.path.dirname(__file__), 'schema.json') if __file__ else 'schema.json'
    print(f"Saving schema to: {save_path}")
    with open(save_path, 'w') as f:
        json.dump(schema, f, indent=4)
        
    print("\nSchema saved successfully. Registered columns and types:")
    for col, dtype in schema.items():
        print(f"  {col}: {dtype}")

if __name__ == '__main__':
    main()
