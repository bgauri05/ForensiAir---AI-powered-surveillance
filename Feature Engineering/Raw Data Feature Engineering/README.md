# RawFE

RawFE is a standalone feature engineering pipeline for Industrial OCEMS telemetry.

It converts raw monitoring data into an ML-ready feature matrix by computing statistical, temporal, correlation, missing-data, and regulatory-limit features.

---

## Project Structure

```text
RawDataFE/
│
├── data/
│   ├── monitoring_data(raw).csv
│   └── consent_limits.csv
│
├── output/
│   └── real_features.parquet
│
└── RawFE/
    ├── config.yaml
    ├── features.py
    ├── loaders.py
    ├── run_raw.py
    ├── validate_schema.py
    ├── schema.json
    ├── requirements.txt
    └── README.md
```

---

## Input Files

### monitoring_data(raw).csv

Expected columns:

| Column | Description |
|---------|-------------|
| factory_id | Factory identifier |
| parameter_id | Sensor / parameter identifier |
| timestamp | Observation timestamp |
| value | Measured value |
| quality_code | Quality flag (ignored) |
| created_at | Record creation time (ignored) |

---

### consent_limits.csv

Expected columns:

| Column | Description |
|---------|-------------|
| factory_id | Factory identifier |
| parameter | Consent parameter name |
| minimum_limit | Regulatory minimum |
| maximum_limit | Regulatory maximum |
| extraction_confidence | Confidence of extracted limit |

---

## Generated Features

The pipeline computes:

- Rolling mean
- Rolling standard deviation
- Coefficient of variation
- Flatline detection
- Rolling autocorrelation
- Missing-rate percentage
- Distance to regulatory limits
- Limit hugging indicators
- Rolling parameter correlations

---

## Output

```
output/real_features.parquet
```

The generated feature matrix contains:

- Original telemetry
- Engineered statistical features
- Temporal features
- Regulatory features
- Correlation features

This output is intended as the input to downstream anomaly detection or machine learning models.

---

## Running the Pipeline

From inside the `RawFE` folder:

```bash
python run_raw.py
```

or specify custom paths:

```bash
python run_raw.py \
    --monitoring-csv ../data/monitoring_data(raw).csv \
    --cto-csv ../data/consent_limits.csv \
    --output-parquet ../output/real_features.parquet
```

---

## Validate Output Schema

Generate the schema file:

```bash
python validate_schema.py
```

This produces:

```
schema.json
```

which documents every generated feature and its datatype.

---

## Configuration

Pipeline parameters are controlled through:

```
config.yaml
```

Examples include:

- rolling window sizes
- flatline thresholds
- autocorrelation lag
- limit hugging percentage

No code changes are required to modify these parameters.

---

## Dependencies

Install dependencies:

```bash
pip install -r requirements.txt
```