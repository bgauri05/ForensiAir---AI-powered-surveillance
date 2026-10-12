import os
import sys
import random
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from loader import normalize_csv, CANONICAL_PARAMS, FACTORY_FILES, DATA_DIR

TAMPER_TYPES = [
    "flatline",
    "copy_paste",
    "limit_hugging",
    "impossible_pH",
    "correlation_break",
    "coordinated_missing_data",
    "gradual_drift"
]

SEVERITIES = ["subtle", "medium", "easy"]

def inject_tamper_windows(factory_name: str, seed: int) -> tuple[pd.DataFrame, list[dict]]:
    """
    Builds a seeded copy of clean telemetry for a factory with 7 injected tamper windows.
    Returns (injected_wide_df, labels_list).
    """
    random.seed(seed)
    np.random.seed(seed)
    
    csv_path = os.path.join(DATA_DIR, FACTORY_FILES[factory_name])
    clean_df = normalize_csv(factory_name, csv_path).copy()
    
    n_rows = len(clean_df)
    # Ensure window index range leaves buffers at start (min index 200) and end (max index n_rows - 500)
    min_idx = 400
    max_idx = n_rows - 500
    
    # We will pick 7 non-overlapping window intervals
    window_lengths = {
        "flatline": {"subtle": 8, "medium": 24, "easy": 72},                # 2h, 6h, 18h
        "copy_paste": {"subtle": 16, "medium": 48, "easy": 96},             # 4h, 12h, 24h
        "limit_hugging": {"subtle": 16, "medium": 32, "easy": 64},          # 4h, 8h, 16h
        "impossible_pH": {"subtle": 8, "medium": 20, "easy": 48},           # 2h, 5h, 12h
        "correlation_break": {"subtle": 48, "medium": 96, "easy": 192},     # 12h, 24h, 48h
        "coordinated_missing_data": {"subtle": 16, "medium": 48, "easy": 120}, # 4h, 12h, 30h
        "gradual_drift": {"subtle": 24, "medium": 48, "easy": 96}           # 6h, 12h, 24h
    }

    # Assign severities deterministically per seed/type
    type_severities = {}
    for i, t in enumerate(TAMPER_TYPES):
        sev_idx = (seed + i) % len(SEVERITIES)
        type_severities[t] = SEVERITIES[sev_idx]

    labels = []
    used_ranges = []

    for t_type in TAMPER_TYPES:
        sev = type_severities[t_type]
        w_len = window_lengths[t_type][sev]
        
        # Find non-overlapping start index
        max_attempts = 100
        start_i = None
        for _ in range(max_attempts):
            cand = random.randint(min_idx, max_idx - w_len)
            cand_end = cand + w_len
            overlap = False
            for r_s, r_e in used_ranges:
                if not (cand_end + 32 <= r_s or cand >= r_e + 32):
                    overlap = True
                    break
            if not overlap:
                start_i = cand
                break
                
        if start_i is None:
            # Fallback sequential allocation if random fails
            start_i = min_idx + len(used_ranges) * 500
            
        end_i = start_i + w_len
        used_ranges.append((start_i, end_i))

        start_time = clean_df.loc[start_i, "timestamp"]
        end_time = clean_df.loc[end_i - 1, "timestamp"]

        # Apply injection logic on clean_df slice
        if t_type == "flatline":
            param = "ETP-BOD"
            # Replace BOD with constant mean value
            val = float(clean_df.loc[start_i:end_i-1, param].mean())
            if np.isnan(val) or val == 0:
                val = 20.0
            clean_df.loc[start_i:end_i-1, param] = val

        elif t_type == "copy_paste":
            param = "ETP-COD"
            # Copy a historical block from 96 steps (24h) prior
            source_start = max(0, start_i - 96)
            source_vals = clean_df.loc[source_start:source_start + w_len - 1, param].values
            if len(source_vals) == w_len:
                clean_df.loc[start_i:end_i-1, param] = source_vals
            else:
                clean_df.loc[start_i:end_i-1, param] = 50.0

        elif t_type == "limit_hugging":
            param = "ETP-BOD"
            upper_lim = 30.0
            if sev == "subtle":
                vals = upper_lim * 0.96 + np.random.normal(0, 0.1, w_len)
            elif sev == "medium":
                vals = upper_lim * 0.98 + np.random.normal(0, 0.05, w_len)
            else:
                vals = upper_lim * 0.995 + np.random.normal(0, 0.01, w_len)
            clean_df.loc[start_i:end_i-1, param] = np.clip(vals, 0, upper_lim)

        elif t_type == "impossible_pH":
            param = "ETP-pH"
            if sev == "subtle":
                vals = 4.9 + np.random.normal(0, 0.1, w_len)  # Violates CTO min limit 5.5
            elif sev == "medium":
                vals = 2.5 + np.random.normal(0, 0.1, w_len)  # Strong acid
            else:
                vals = 13.5 + np.random.normal(0, 0.1, w_len) # Extreme alkaline
            clean_df.loc[start_i:end_i-1, param] = np.clip(vals, 0, 14)

        elif t_type == "correlation_break":
            # Decouple BOD and COD
            bod_vals = clean_df.loc[start_i:end_i-1, "ETP-BOD"].values
            if sev == "subtle":
                # Invert BOD noise
                clean_df.loc[start_i:end_i-1, "ETP-BOD"] = bod_vals[::-1] + np.random.normal(0, 2.0, w_len)
            elif sev == "medium":
                # Random uncorrelated noise
                clean_df.loc[start_i:end_i-1, "ETP-BOD"] = np.random.uniform(10.0, 45.0, w_len)
            else:
                # Anti-correlation: spike BOD high while COD drops low
                clean_df.loc[start_i:end_i-1, "ETP-BOD"] = 45.0 + np.random.normal(0, 1.0, w_len)
                clean_df.loc[start_i:end_i-1, "ETP-COD"] = 25.0 + np.random.normal(0, 1.0, w_len)

        elif t_type == "coordinated_missing_data":
            # Set all parameter values in window to NaN
            for p in ["ETP-BOD", "ETP-COD", "ETP-pH", "ETP-Flow", "ETP-TSS"]:
                if p in clean_df.columns:
                    clean_df.loc[start_i:end_i-1, p] = np.nan

        elif t_type == "gradual_drift":
            param = "ETP-COD"
            orig_vals = clean_df.loc[start_i:end_i-1, param].values
            if sev == "subtle":
                decay = np.linspace(1.0, 0.85, w_len)
            elif sev == "medium":
                decay = np.linspace(1.0, 0.65, w_len)
            else:
                decay = np.linspace(1.0, 0.40, w_len)
            clean_df.loc[start_i:end_i-1, param] = orig_vals * decay

        labels.append({
            "factory": factory_name,
            "seed": seed,
            "type": t_type,
            "start": str(start_time),
            "end": str(end_time),
            "start_idx": start_i,
            "end_idx": end_i,
            "severity": sev,
            "window_steps": w_len
        })

    return clean_df, labels

def generate_all_injections(seeds: list[int] = [42, 43, 44, 45]) -> tuple[dict, pd.DataFrame]:
    """
    Generates seeded copies for all 4 factories across specified seeds.
    Returns (injected_wide_dfs_dict, labels_df).
    """
    factories = ["Cipla", "Glenmark", "Indoco", "Zydus"]
    all_labels = []
    injected_dfs = {}

    print(f"Generating seeded injection datasets across {len(factories)} factories and {len(seeds)} seeds...")
    for f in factories:
        for s in seeds:
            key = f"{f}_seed_{s}"
            inj_wide, labels = inject_tamper_windows(f, s)
            injected_dfs[key] = inj_wide
            all_labels.extend(labels)

    labels_df = pd.DataFrame(all_labels)
    out_labels_path = os.path.join(REPO_ROOT, "validation_unseen", "injection_labels.csv")
    labels_df.to_csv(out_labels_path, index=False)
    print(f"Saved injection ground truth manifest ({len(labels_df)} events) to {out_labels_path}")

    return injected_dfs, labels_df

if __name__ == "__main__":
    inj_dfs, labels_df = generate_all_injections()
    print("Sample generated labels:")
    print(labels_df.head(10).to_string(index=False))
