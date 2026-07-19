# ForensiAIR Feature Engineering Package (`forensiair_features`)

This package is designed as one half of a collaborative two-PC pipeline to compute diagnostic and fraud-detection features for the ForensiAIR OCEMS classifier. Both PCs share the identical, dataset-agnostic feature extraction logic in `features.py` to maintain exact engineering parity.

## Pipeline Structure
- **This PC (Synthetic)**: Generates the features from simulated CY2024 monitoring data and labels.
- **Other PC (Real-Data)**: Clones the repository at the same commit, implements the postgres database loader `load_real()` in `loaders.py`, and runs feature extraction over real-world dataset.

## Installation
Ensure dependencies match versions exactly:
```bash
pip install -r requirements.txt
```

## Running the Pipeline
To run feature engineering on the synthetic dataset:
```bash
python run_synthetic.py --monitoring-csv ../output/monitoring_data.csv --labels-csv ../output/labels.csv
```

## Verification & Parity Check
After running, extract the schema of the generated Parquet using:
```bash
python validate_schema.py
```
This generates a `schema.json` containing the registered columns and data types. Commit `schema.json` to the repository so the real-data PC can diff its output structure and ensure schema compatibility.
