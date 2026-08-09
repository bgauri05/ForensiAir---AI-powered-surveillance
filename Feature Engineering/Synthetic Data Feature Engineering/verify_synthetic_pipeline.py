import os
import pandas as pd
import numpy as np

def verify():
    parquet_path = '../../Data/SynData/synthetic_features.parquet'
    if not os.path.exists(parquet_path):
        parquet_path = 'Data/SynData/synthetic_features.parquet'

    print(f"Loading parquet for verification: {parquet_path}")
    df = pd.read_parquet(parquet_path)

    print("\n--- 1. Check Row Count & Data Types ---")
    print(f"Total Rows: {len(df)}")
    print(f"Total Columns: {len(df.columns)}")

    print("\n--- 2. Tamper Types Breakdown ---")
    print(df['tamper_type'].value_counts(dropna=False))

    print("\n--- 3. Verify Events Span Full Year 2024 (H1 vs H2) ---")
    df['half_year'] = np.where(df['timestamp'].dt.month <= 6, 'H1', 'H2')
    h1_h2_tamper = df.groupby(['tamper_type', 'half_year']).size().unstack(fill_value=0)
    print(h1_h2_tamper)

    print("\n--- 4. Verify Factory Level H1 vs H2 Presence for New Tamper Types ---")
    new_tampers = ['BDL GAMING', 'NEGATIVE VALUES', 'DUPLICATE RUN']
    fac_h1_h2 = df[df['tamper_type'].isin(new_tampers)].groupby(['factory_id', 'tamper_type', 'half_year']).size().unstack(fill_value=0)
    print(fac_h1_h2)

    print("\n--- 5. Verify Zero Infinities across all numeric features ---")
    num_cols = df.select_dtypes(include=[np.number]).columns
    inf_sums = {col: int(np.isinf(df[col]).sum()) for col in num_cols if np.isinf(df[col]).sum() > 0}
    print(f"Infinite counts across numeric columns: {inf_sums}")
    assert len(inf_sums) == 0, "Error: Infinities found!"

    print("\n--- 6. Verify Negative Values Distribution ---")
    neg_by_param = df[df['value'] < 0].groupby('parameter_id').size()
    print(neg_by_param)
    assert not neg_by_param.empty, "Error: Expected negative values for non-pH parameters!"

    print("\n--- 7. Verify New Feature Columns Nulls and Stats ---")
    new_cols = ['bdl_rate', 'duplicate_run_length', 'cov_severity', 'bod_cod_ratio', 'bod_cod_ratio_volatility']
    for c in new_cols:
        assert c in df.columns, f"Missing column {c}"
        print(f"{c}: dtype={df[c].dtype}, non-nulls={df[c].notna().sum()}/{len(df)}")

    print("\n>>> ALL VERIFICATION CHECKS PASSED SUCCESSFULLY! <<<")

if __name__ == '__main__':
    verify()
