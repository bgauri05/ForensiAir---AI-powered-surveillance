import os
import random
import pandas as pd
import numpy as np

SEED = 42

def generate_and_inject_tampers(
    monitoring_csv_path: str = "../../Data/SynData/monitoring_data.csv",
    labels_csv_path: str = "../../Data/SynData/labels.csv",
    seed: int = SEED
):
    print(f"Setting random seed: {seed}")
    np.random.seed(seed)
    random.seed(seed)

    print(f"Loading existing synthetic datasets:\n  Monitoring: {monitoring_csv_path}\n  Labels: {labels_csv_path}")
    df_mon = pd.read_csv(monitoring_csv_path)
    df_lab = pd.read_csv(labels_csv_path)

    df_mon['timestamp'] = pd.to_datetime(df_mon['timestamp'])
    df_lab['start_timestamp'] = pd.to_datetime(df_lab['start_timestamp'])
    df_lab['end_timestamp'] = pd.to_datetime(df_lab['end_timestamp'])

    # Strip previous appended injection events to prevent accumulation across script reruns
    base_tampers = [
        'INSPECTION DIP', 'CORRELATION BREAK', 'LIMIT HUGGING', 'COPY-PASTE', 
        'FLATLINE', 'COORDINATED MISSING DATA', 'IMPOSSIBLE PH RANGE', 
        'SENSOR FREEZE', 'NIGHTTIME ZERO SHUTDOWN', 'EXTREME SPIKE', 'CALIBRATION DRIFT'
    ]
    df_lab = df_lab[df_lab['tamper_type'].isin(base_tampers)].copy()

    # 1. Unify IMPOSSIBLE PH RANGE -> NEGATIVE VALUES
    df_lab['tamper_type'] = df_lab['tamper_type'].replace({'IMPOSSIBLE PH RANGE': 'NEGATIVE VALUES'})
    df_mon['tamper_type'] = df_mon['tamper_type'].replace({'IMPOSSIBLE PH RANGE': 'NEGATIVE VALUES'})


    # Add quality_code if missing (default 'Raw')
    if 'quality_code' not in df_mon.columns:
        df_mon['quality_code'] = 'Raw'

    # Baseline BDL rate (~0.8% of normal observations set to 'L')
    untampered_mask = df_mon['tamper_type'].isna()
    untampered_indices = df_mon[untampered_mask].index.to_numpy()
    num_baseline_bdl = int(len(untampered_indices) * 0.008)
    baseline_bdl_indices = np.random.choice(untampered_indices, size=num_baseline_bdl, replace=False)
    
    df_mon.loc[baseline_bdl_indices, 'quality_code'] = 'L'
    df_mon.loc[baseline_bdl_indices, 'value'] = np.random.uniform(0.0, 0.05, size=num_baseline_bdl)

    # Get exact valid parameters per factory
    factory_params_map = df_mon.groupby('factory_id')['parameter_id'].unique().to_dict()
    factories = list(factory_params_map.keys())

    new_labels = []

    # Helper function to check overlap
    def has_overlap(fac, param, start_ts, end_ts, current_labels_df, new_labels_list):
        sub1 = current_labels_df[(current_labels_df['factory_id'] == fac) & (current_labels_df['parameter_id'] == param)]
        for _, r in sub1.iterrows():
            if max(start_ts, r['start_timestamp']) <= min(end_ts, r['end_timestamp']):
                return True
        for nl in new_labels_list:
            if nl['factory_id'] == fac and nl['parameter_id'] == param:
                if max(start_ts, nl['start_timestamp']) <= min(end_ts, nl['end_timestamp']):
                    return True
        return False

    # ----------------------------------------------------
    # TAMPER 1: BDL GAMING (~2-4k rows total across 13 factories)
    # ----------------------------------------------------
    print("Generating BDL GAMING events...")
    for fac in factories:
        avail_params = factory_params_map[fac]
        non_ph_params = [p for p in avail_params if p != 'ETP-pH']
        target_params = non_ph_params if len(non_ph_params) > 0 else avail_params

        for period, start_range, end_range in [
            ("H1", "2024-01-15", "2024-06-15"),
            ("H2", "2024-07-15", "2024-12-15")
        ]:
            # 2 events per half-year per factory
            for _ in range(2):
                attempts = 0
                while attempts < 100:
                    attempts += 1
                    param = random.choice(target_params)
                    random_days = random.randint(0, 100)
                    start_ts = (pd.to_datetime(start_range) + pd.Timedelta(days=random_days, hours=random.randint(0, 23), minutes=15*random.randint(0, 3))).floor('15min')
                    duration_steps = random.randint(48, 72) # 12 to 18 hours (~60 rows)
                    end_ts = start_ts + pd.Timedelta(minutes=15 * (duration_steps - 1))

                    if not has_overlap(fac, param, start_ts, end_ts, df_lab, new_labels):
                        severity = random.choice(['low', 'medium', 'high'])
                        new_labels.append({
                            'factory_id': fac,
                            'parameter_id': param,
                            'tamper_type': 'BDL GAMING',
                            'start_timestamp': start_ts,
                            'end_timestamp': end_ts,
                            'severity': severity
                        })
                        break

    # ----------------------------------------------------
    # TAMPER 2: NEGATIVE VALUES (~2-4k rows total across 13 factories)
    # ----------------------------------------------------
    print("Generating NEGATIVE VALUES events for non-pH parameters...")
    for fac in factories:
        avail_params = factory_params_map[fac]
        non_ph_params = [p for p in avail_params if p != 'ETP-pH']
        target_params = non_ph_params if len(non_ph_params) > 0 else avail_params

        for period, start_range, end_range in [
            ("H1", "2024-01-20", "2024-06-20"),
            ("H2", "2024-07-20", "2024-12-20")
        ]:
            # 2 events per half-year per factory
            for _ in range(2):
                attempts = 0
                while attempts < 100:
                    attempts += 1
                    param = random.choice(target_params)
                    random_days = random.randint(0, 100)
                    start_ts = (pd.to_datetime(start_range) + pd.Timedelta(days=random_days, hours=random.randint(0, 23), minutes=15*random.randint(0, 3))).floor('15min')
                    duration_steps = random.randint(36, 60) # 9 to 15 hours (~48 rows)
                    end_ts = start_ts + pd.Timedelta(minutes=15 * (duration_steps - 1))

                    if not has_overlap(fac, param, start_ts, end_ts, df_lab, new_labels):
                        severity = random.choice(['low', 'medium', 'high'])
                        new_labels.append({
                            'factory_id': fac,
                            'parameter_id': param,
                            'tamper_type': 'NEGATIVE VALUES',
                            'start_timestamp': start_ts,
                            'end_timestamp': end_ts,
                            'severity': severity
                        })
                        break

    # ----------------------------------------------------
    # TAMPER 3: DUPLICATE RUN (~2-4k rows total across 13 factories)
    # ----------------------------------------------------
    print("Generating DUPLICATE RUN events...")
    for fac in factories:
        avail_params = factory_params_map[fac]
        for period, start_range, end_range in [
            ("H1", "2024-01-10", "2024-06-25"),
            ("H2", "2024-07-10", "2024-12-25")
        ]:
            # 8 events per half-year per factory (~12 steps per event = ~1500-2500 rows)
            for _ in range(8):
                attempts = 0
                while attempts < 100:
                    attempts += 1
                    param = random.choice(avail_params)
                    random_days = random.randint(0, 140)
                    start_ts = (pd.to_datetime(start_range) + pd.Timedelta(days=random_days, hours=random.randint(0, 23), minutes=15*random.randint(0, 3))).floor('15min')
                    duration_steps = random.randint(6, 20) # 6 to 20 consecutive readings
                    end_ts = start_ts + pd.Timedelta(minutes=15 * (duration_steps - 1))

                    if not has_overlap(fac, param, start_ts, end_ts, df_lab, new_labels):
                        severity = random.choice(['low', 'medium', 'high'])
                        new_labels.append({
                            'factory_id': fac,
                            'parameter_id': param,
                            'tamper_type': 'DUPLICATE RUN',
                            'start_timestamp': start_ts,
                            'end_timestamp': end_ts,
                            'severity': severity
                        })
                        break

    new_labels_df = pd.DataFrame(new_labels)
    df_lab_updated = pd.concat([df_lab, new_labels_df], ignore_index=True)

    # ----------------------------------------------------
    # Apply modifications to df_mon
    # ----------------------------------------------------
    print("Applying tamper modifications to monitoring telemetry...")

    df_mon = df_mon.sort_values(by=['factory_id', 'parameter_id', 'timestamp']).reset_index(drop=True)

    for idx, row in new_labels_df.iterrows():
        mask = (
            (df_mon['factory_id'] == row['factory_id']) &
            (df_mon['parameter_id'] == row['parameter_id']) &
            (df_mon['timestamp'] >= row['start_timestamp']) &
            (df_mon['timestamp'] <= row['end_timestamp'])
        )

        if not mask.any():
            continue

        df_mon.loc[mask, 'tamper_type'] = row['tamper_type']

        if row['tamper_type'] == 'BDL GAMING':
            sub_indices = df_mon[mask].index.to_numpy()
            n_bdl = max(1, int(len(sub_indices) * 0.85))
            chosen = np.random.choice(sub_indices, size=n_bdl, replace=False)
            df_mon.loc[chosen, 'quality_code'] = 'L'
            df_mon.loc[chosen, 'value'] = np.random.uniform(0.0, 0.05, size=n_bdl)

        elif row['tamper_type'] == 'NEGATIVE VALUES':
            sub_len = mask.sum()
            df_mon.loc[mask, 'value'] = np.random.uniform(-50.0, -2.0, size=sub_len)
            df_mon.loc[mask, 'quality_code'] = 'Raw'

        elif row['tamper_type'] == 'DUPLICATE RUN':
            base_val = float(np.round(np.random.uniform(10.0, 85.0), 3))
            df_mon.loc[mask, 'value'] = base_val
            df_mon.loc[mask, 'quality_code'] = 'Raw'

    # Format timestamps back to string for clean CSV output
    df_mon['timestamp'] = df_mon['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df_lab_updated['start_timestamp'] = df_lab_updated['start_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df_lab_updated['end_timestamp'] = df_lab_updated['end_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

    print(f"Saving updated labels to: {labels_csv_path}")
    df_lab_updated.to_csv(labels_csv_path, index=False)

    print(f"Saving updated monitoring telemetry to: {monitoring_csv_path}")
    df_mon.to_csv(monitoring_csv_path, index=False)

    print("Injection process completed successfully!")

if __name__ == '__main__':
    generate_and_inject_tampers(seed=SEED)
