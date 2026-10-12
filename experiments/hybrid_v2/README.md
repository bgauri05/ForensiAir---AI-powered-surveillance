# 🔬 Hybrid v2 Semi-Synthetic Dataset Experiment (`experiments/hybrid_v2`)

This directory contains the complete Phase B data generation, feature engineering, integrity verification, and unit test suite for the **Hybrid v2** semi-synthetic environmental telemetry dataset.

---

## 📌 Experiment Structure

```text
experiments/hybrid_v2/
├── README.md                                    # Master experiment documentation (this file)
├── data_readiness_report.md                    # Phase A audit & readiness report
├── checksums.txt                                # SHA256 integrity checksums of original reference files
│
├── ⚙️ Pipeline Scripts
├── generate_hybrid_v2.py                       # Phase B telemetry generator (320 events, subtle rules, 2 variants)
├── rebuild_features.py                          # 28-column feature matrix builder using real pipeline code
└── test_manifest.py                            # PyUnit unit tests verifying manifest and feature integrity
│
├── 📊 Generated Datasets & Manifests
├── control_telemetry.parquet / .csv             # Untouched baseline control copy
├── hybrid_v2_code_neutral_telemetry.parquet/.csv# Variant 1: Original quality codes preserved
├── hybrid_v2_code_visible_telemetry.parquet/.csv# Variant 2: Quality codes updated to reflect tamper state
├── tamper_manifest.csv                         # Ground truth manifest (320 events, severities, window ranges)
│
└── 🧮 Rebuilt Feature Matrices (28 Columns matching real_features.parquet)
├── control_features.parquet                     # Control copy feature matrix
├── hybrid_v2_code_neutral_features.parquet     # Variant 1 feature matrix
└── hybrid_v2_code_visible_features.parquet     # Variant 2 feature matrix
```

---

## 🚀 Execution & Reproduction Instructions

To reproduce the dataset generation, feature extraction, and unit test verification from scratch, execute the following commands from the repository root:

### 1. Run Phase B Hybrid v2 Telemetry Generator
Generates the 320 balanced tamper events across the 4 valid sites (`site_1129`, `site_1307`, `site_1629`, `site_1631`), applies subtle severity rules, and outputs both `code-neutral` and `code-visible` variants alongside `tamper_manifest.csv`:

```bash
python experiments/hybrid_v2/generate_hybrid_v2.py
```

### 2. Rebuild Feature Matrices using Real Pipeline Code
Imports `assemble_feature_matrix` from `Feature Engineering/Synthetic Data Feature Engineering/features.py` and extracts the complete 28-column feature matrix for the control copy and both variants:

```bash
python experiments/hybrid_v2/rebuild_features.py
```

### 3. Run PyUnit Test Suite
Runs full unit tests asserting manifest event counts ($\ge 300$), multi-day copy-paste windows ($\ge 192$ steps), detector tagging, data window match exactness, and 28-column schema alignment with `real_features.parquet`:

```bash
python experiments/hybrid_v2/test_manifest.py
```

---

## 🛡️ Integrity & Non-Overlap Guarantees
- **SHA256 File Checksums**: Recorded in `checksums.txt` before and after execution to prove original reference files (`real_features.parquet`, `forensier.db`, raw CSV exports) remain 100% untouched.
- **Event Non-Overlap**: No event overlaps another.
- **Baseline Exclusions**: Events never start inside data gaps $> 1\text{h}$ or existing baseline flatlines $> 6\text{h}$, and maintain a 24-hour buffer from time-series edges.
- **BDL Gaming Detector**: Explicitly marked as `detector_type = "none"`.
