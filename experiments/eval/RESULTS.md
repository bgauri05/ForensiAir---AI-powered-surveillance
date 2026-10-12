# ForensiAIR Performance & Baseline Evaluation Results

## Executive Summary

- **Subtle-Severity Detection Recall**: **95.65%** (66/69 events detected, 95% Wilson CI: **[87.8%, 98.5%]**).
- **Control Untouched False-Alarm Flag Rate**: **873.90 flags per site-month** across 21 site-months of untouched baseline data.
- **Baseline Superiority**: ForensiAIR outperforms a calibrated rolling z-score detector at the exact same false-alarm level ($z_{thresh} = 1.2462$) by **+5.8%** on subtle tampering events (95.65% vs 89.86%).

---

## 1. Headline Detection Recall by Severity

Headline detection excludes `ETP-Flow` / `Flow` parameters (52 events) and separately reported categories (`BDL GAMING` and `INSPECTION DIP`).

| Severity | Event Count ($n$) | Detected Events | Recall Rate | 95% Wilson Confidence Interval |
| :--- | :---: | :---: | :---: | :---: |
| **Subtle** | 69 | 66 | **95.65%** | **[87.8%, 98.5%]** |
| **Medium** | 72 | 64 | **88.89%** | **[79.5%, 94.3%]** |
| **Easy** | 57 | 52 | **91.23%** | **[81.1%, 96.2%]** |
| **Overall** | 198 | 182 | **91.92%** | **[87.3%, 95.0%]** |

---

## 2. Separately Reported Tamper Types

As specified in `config.yaml`, `BDL GAMING` and `INSPECTION DIP` are evaluated and reported separately from the headline metrics:

| Tamper Type | Severity | Event Count ($n$) | Detected Events | Recall Rate | 95% Wilson CI |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **BDL GAMING** | Subtle | 10 | 10 | **100.0%** | [72.2%, 100.0%] |
| **BDL GAMING** | Medium | 10 | 10 | **100.0%** | [72.2%, 100.0%] |
| **BDL GAMING** | Easy | 15 | 15 | **100.0%** | [79.6%, 100.0%] |
| **INSPECTION DIP** | Subtle | 10 | 10 | **100.0%** | [72.2%, 100.0%] |
| **INSPECTION DIP** | Medium | 10 | 10 | **100.0%** | [72.2%, 100.0%] |
| **INSPECTION DIP** | Easy | 15 | 15 | **100.0%** | [79.6%, 100.0%] |

---

## 3. Control Untouched Data Flag Rate

Baseline false-alarm rate computed on untouched control telemetry (114,509 records across 5 sites and 21 site-months):

| Site ID | Site-Months Monitored | Total False Flags | Flags per Site-Month |
| :--- | :---: | :---: | :---: |
| `site_1129` | 4 | 3,495 | 873.75 |
| `site_1307` | 5 | 4,370 | 874.00 |
| `site_1458` | 4 | 3,496 | 874.00 |
| `site_1629` | 4 | 3,495 | 873.75 |
| `site_1631` | 4 | 3,496 | 874.00 |
| **Total / Mean** | **21** | **18,352** | **873.90** |

---

## 4. Risk Score Impact Before vs After Injection

Risk scores increase significantly following injection across all severities:

| Severity | Risk Score Before (Control) | Risk Score After (Injected) | $\Delta$ Risk Score |
| :--- | :---: | :---: | :---: |
| **Subtle** | 14.11 | 19.85 | **+5.74** |
| **Medium** | 14.11 | 20.32 | **+6.21** |
| **Easy** | 14.11 | 20.58 | **+6.47** |
| **Overall Mean** | 14.11 | 20.21 | **+6.10** |

---

## 5. Model vs Rolling Z-Score Baseline Comparison

Calibrated at the exact same false-alarm level ($z_{thresh} = 1.2462$):

| Severity | Event Count ($n$) | ForensiAIR Recall | Baseline Z-Score Recall | Improvement ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: |
| **Subtle** | 69 | **95.65%** | 89.86% | **+5.8%** |
| **Medium** | 72 | **88.89%** | 84.72% | **+4.2%** |
| **Easy** | 57 | **91.23%** | 85.96% | **+5.3%** |
| **Overall** | 198 | **91.92%** | 86.87% | **+5.1%** |

---

## 6. Generated Visualizations

1. `baseline_vs_forensiair.png`: Comparison bar chart showing detection recall gain over the calibrated rolling z-score baseline.
2. `control_flag_rate_by_site.png`: Distribution of false-alarm flag rates per site-month across untouched control data.
