# ForensiAIR Data Contamination Statement

This document details baseline data contamination across the 33 Dev factories and 4 Locked Test factories, and defines candidate exclusion rules for clean telemetry evaluation.

---

## 1. Per-Factory Contamination Metrics

| Set | Factory ID | Total Rows | % Invalid Values | % Non-Raw Quality Code | Longest Gap (Hours) | % Rows in Exact-Repeat Runs (>= 2h) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| Dev | `site_1131` | 31,048 | 0.0% | 0.0% | 220.5h | 99.17% |
| Dev | `site_1138` | 30,839 | 0.0% | 99.92% | 255.25h | 99.92% |
| Dev | `site_1167` | 7,650 | 0.0% | 0.0% | 1322.0h | 100.0% |
| Dev | `site_1200` | 33,303 | 0.0% | 0.0% | 157.0h | 91.79% |
| Dev | `site_1203` | 31,375 | 0.0% | 0.93% | 326.0h | 99.99% |
| Dev | `site_1221` | 63,588 | 0.0% | 0.01% | 95.0h | 60.55% |
| Dev | `site_1232` | 56,924 | 0.0% | 50.0% | 360.0h | 54.72% |
| Dev | `site_1247` | 25,956 | 0.0% | 0.0% | 1355.5h | 99.35% |
| Dev | `site_1256` | 1,562 | 0.0% | 0.0% | 354.75h | 51.73% |
| Dev | `site_1257` | 62,186 | 0.0% | 0.11% | 366.75h | 33.27% |
| Dev | `site_1259` | 8,107 | 0.01% | 32.45% | 1364.5h | 64.93% |
| Dev | `site_1264` | 43,732 | 0.0% | 0.01% | 2040.25h | 67.44% |
| Dev | `site_1280` | 29,686 | 0.0% | 0.58% | 167.25h | 0.06% |
| Dev | `site_1281` | 43,300 | 17.95% | 33.5% | 1202.75h | 60.86% |
| Dev | `site_1284` | 42,048 | 0.0% | 15.37% | 1166.25h | 54.87% |
| Dev | `site_1285` | 60,402 | 0.01% | 12.93% | 900.25h | 60.06% |
| Dev | `site_1310` | 27,740 | 0.0% | 0.0% | 1607.0h | 11.18% |
| Dev | `site_1321` | 58,278 | 0.0% | 0.0% | 120.5h | 33.26% |
| Dev | `site_1369` | 87,457 | 0.01% | 5.87% | 353.25h | 33.62% |
| Dev | `site_1376` | 92,679 | 0.0% | 1.36% | 67.25h | 36.42% |
| Dev | `site_1561` | 32,920 | 0.0% | 4.96% | 244.75h | 67.27% |
| Dev | `site_1569` | 5,310 | 0.0% | 0.0% | 1.75h | 100.0% |
| Dev | `site_1581` | 274 | 0.36% | 4.01% | 3575.25h | 50.73% |
| Dev | `site_1668` | 87,431 | 0.0% | 28.78% | 25.0h | 27.47% |
| Dev | `site_1756` | 51,559 | 0.0% | 0.0% | 184.75h | 56.88% |
| Dev | `site_1787` | 34,161 | 0.0% | 0.6% | 24.5h | 0.0% |
| Dev | `site_1789` | 6,429 | 0.0% | 0.86% | 3118.0h | 50.3% |
| Dev | `site_1799` | 74,565 | 0.09% | 0.0% | 144.0h | 36.64% |
| Dev | `site_1905` | 15,762 | 0.0% | 0.0% | 884.5h | 94.36% |
| Dev | `site_1909` | 7,224 | 0.01% | 0.03% | 573.5h | 62.24% |
| Dev | `site_2070` | 559 | 0.0% | 0.0% | 24.0h | 22.36% |
| Dev | `site_887` | 89,025 | 0.0% | 0.44% | 29.0h | 28.16% |
| Dev | `site_982` | 11,380 | 0.0% | 0.0% | 11.5h | 0.0% |

---

## 2. Proposed Rules for "Clean" Telemetry & Exclusion Impact

| Rule Level | Rule Definition | Excluded Rows (Dev Set) | % Dev Data Excluded | Rationale |
| :--- | :--- | :---: | :---: | :--- |
| **Rule 1 (Strict)** | `quality_code == 'Raw'` AND `val >= 0` AND `run_length < 8` | **409,692** | **32.66%** | Eliminates error codes, invalid values, and natural zero-flow shutdown flatlines |
| **Rule 2 (Moderate)** | `quality_code in ['Raw', 'L']` AND `val >= 0` | **116,395** | **9.28%** | Matches current production quality filter (drops Error & Out of Range) |
| **Rule 3 (Permissive)** | `value.notna()` AND `val >= 0` (No quality filter) | **1,241** | **0.10%** | Keeps all readable sensor records except corrupt negative/sentinel values |
