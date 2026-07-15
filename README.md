# Industrial Environmental Data Tampering Detection System

An AI-powered anomaly detection system that identifies suspicious tampering patterns in Industrial Online Continuous Environmental Monitoring System (OCEMS) telemetry using Machine Learning and Explainable AI.

> **Project Status:** Work in Progress

---

# Overview

Industrial facilities continuously transmit environmental telemetry such as pH, COD, BOD, TSS, Flow, SO₂, NOx, and other pollution parameters to regulatory authorities through OCEMS.

This project aims to detect suspicious telemetry manipulation by analyzing behavioral patterns rather than relying solely on threshold violations.

Instead of checking whether pollution exceeds legal limits, the system identifies possible evidence of data tampering using engineered **Tampering Fingerprints** combined with Machine Learning.

---

# 🚀 Features

- Industrial telemetry preprocessing
- Synthetic tampering dataset generation
- Tampering Fingerprint Engine
- Isolation Forest anomaly detection
- One-Class SVM anomaly detection
- XGBoost supervised classifier
- SHAP Explainable AI
- Risk score generation
- FastAPI backend
- React dashboard
- PostgreSQL database

---

# Tampering Fingerprints

The project extracts multiple behavioral fingerprints from telemetry including:

- Flatline Detection
- Correlation Break
- Gradual Drift
- Limit Hugging
- Copy-Paste Detection
- Coordinated Missing Data
- Pre-Inspection Cleanup
- Impossible Sensor Values

These fingerprints become the feature vector used by the Machine Learning models.

---

# Machine Learning Pipeline

```text
Raw OCEMS Telemetry
        │
        ▼
Data Cleaning
        │
        ▼
Feature Engineering
        │
        ▼
Tampering Fingerprint Extraction
        │
        ▼
Synthetic Tamper Injection
        │
        ▼
Model Training
(Isolation Forest + One-Class SVM + XGBoost)
        │
        ▼
SHAP Explainability
        │
        ▼
Risk Score Generation
```

---

# Tech Stack

### Backend

- Python
- FastAPI

### Machine Learning

- Scikit-Learn
- XGBoost
- SHAP
- Pandas
- NumPy

### Frontend

- React
- HTML
- CSS
- JavaScript

### Database

- PostgreSQL

---

# Project Structure

```
backend/
frontend/
ml_pipeline/
database/
datasets/
docs/
tests/
reports/
```

---

# Current Status

This project is currently under active development.

Completed

- Literature Review
- Dataset Collection
- Data Profiling
- Project Architecture

In Progress

- Feature Engineering
- Synthetic Tamper Generation
- Machine Learning Pipeline

Planned

- FastAPI Integration
- React Dashboard
- Explainable AI
- Model Deployment

---

# Future Scope

- Real-time OCEMS monitoring
- Live anomaly detection
- Blockchain-backed audit logging
- Automatic regulator alerts
- Digital twin simulation

---

# 📜 License

This project is developed for academic and research purposes.
