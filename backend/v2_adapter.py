"""
backend/v2_adapter.py
=====================
Lightweight V2 Adapter for ForensiAIR Backend.

Integrates the validated ForensiAIR V2 detector artifacts (validation_v2/v2/model/)
into the application backend API without modifying existing V1 files or retraining models.

Data Contracts:
- GET /api/v2/model-info: Model architecture, feature set, calibrated budget, and reconciled metrics.
- GET /api/v2/alerts: Validated V2 alert episodes with timestamps, parameter, category, duration, evidence.
- GET /api/factories/{fid}/v2-analysis: Factory-specific V2 performance, clean false-alarm rate, and event history.

Safety & Protocol Rules:
- Development data only: 33 permitted development factories.
- Strictly isolated: Data/Unseen/ and locked factories (Cipla, Glenmark, Indoco, Zydus) NEVER accessed.
- Distinguishes historical development evaluation results from live inference.
- Explicitly documents that 1.0 false-alert/factory-month calibration is a development benchmark, not a production guarantee.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
V2_MODEL_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "model")
V2_EVAL_EVENTS_CSV = os.path.join(V2_MODEL_DIR, "v2_eval_events.csv")
V2_CLEAN_FA_CSV = os.path.join(V2_MODEL_DIR, "v2_clean_false_alarms.csv")
V2_METHODS_CSV = os.path.join(V2_MODEL_DIR, "v2_methods_comparison.csv")

# Regulatory & Legal Disclaimer
MANDATORY_V2_DISCLAIMER = (
    "ForensiAIR V2 detects statistical and mathematical anomalies in industrial telemetry under "
    "a calibrated operating budget of 1.0 false alert per factory-month. Detections reflect "
    "synthetic anomalous behavior patterns and do not constitute legal or regulatory proof "
    "of deliberate physical tampering."
)

# Factory ID to friendly name mapping
FACTORY_NAMES = {
    "site_1131": ("RUPA ORGANICS PVT LTD. Taloja", "Taloja", "Chemical Manufacturing"),
    "site_1138": ("Nixon Chemicals Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1167": ("Super Petroleum Products Private Limited", "Taloja", "Petrochemical Refinery"),
    "site_1200": ("Metallurgical Products India(P) Ltd", "Taloja", "Heavy Metallurgy"),
    "site_1203": ("Anmol Chemicals Pvt. Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1221": ("Zirconium Chemicals Pvt. Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1232": ("M/s.Altaroma Chemicals Pvt Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1247": ("Ducol Organics & Colours Pvt Ltd", "Taloja", "Garment & Dyeing"),
    "site_1256": ("SHREE VINAYAK ORGANICS (I) PVT LTD", "Taloja", "Chemical Manufacturing"),
    "site_1257": ("Dorf Ketal Chemicals India Pvt Ltd", "Taloja", "Petrochemical Refinery"),
    "site_1259": ("EUROCHEM INDUSTRIES", "Taloja", "Chemical Manufacturing"),
    "site_1264": ("Imagico India Pvt Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1280": ("EKVIRA FINE CHEM PVT LTD", "Taloja", "Chemical Manufacturing"),
    "site_1281": ("M/s RAMDEV CHEMI-Pharma PVT LTD", "Taloja", "Pharmaceutical Synthetics"),
    "site_1284": ("CORROGARD CHEMICALS", "Taloja", "Chemical Manufacturing"),
    "site_1285": ("VVL Pharma Pvt Ltd", "Taloja", "Pharmaceutical Synthetics"),
    "site_1310": ("Aezis Global Pvt Ltd", "Mahad", "Chemical Manufacturing"),
    "site_1321": ("M/s. Indo Amines Ltd.", "Mahad", "Drugs and Pharmaceuticals"),
    "site_1369": ("M/s.Privi Specialty Chemicals Ltd(Unit-II)", "Mahad", "Chemical Manufacturing"),
    "site_1376": ("M/s.Privi Speciality Chemicals Limited Unit III", "Mahad", "Chemical Manufacturing"),
    "site_1561": ("GRASIM INDUSTRIES LIMITED", "Mahad", "Chemical Manufacturing"),
    "site_1569": ("M/s.Galaxy Surfactants Limited", "Taloja", "Chemical Manufacturing"),
    "site_1581": ("M/s Memba Chem Industries Private Limited", "Taloja", "Chemical Manufacturing"),
    "site_1668": ("Nouryon Chemicals India Private Limited", "Mahad", "Chemical Manufacturing"),
    "site_1756": ("M/s. Aquapharm Chemicals Pvt. Ltd.", "Mahad", "Chemical Manufacturing"),
    "site_1787": ("SHREE HARI CHEMICALS EXPORT LIMITED", "Mahad", "Chemical Manufacturing"),
    "site_1789": ("sudarshan chemical industries ltd Mahad", "Mahad", "Chemical Manufacturing"),
    "site_1799": ("Privi Speciality Chemicals Limited Unit 10", "Mahad", "Chemical Manufacturing"),
    "site_1905": ("Allnex Resins India Pvt ltd", "Mahad", "Synthetic Rubber"),
    "site_1909": ("Cyklo Pharma Chem Pvt Ltd", "Taloja", "Pharmaceutical Synthetics"),
    "site_2070": ("Prigiv Specialties Pvt Ltd", "Mahad", "Chemical Manufacturing"),
    "site_887": ("Dow Chemical International Pvt Ltd", "Taloja", "Chemical Manufacturing"),
    "site_982": ("PREETI PETROCHEM PVT LTD", "Taloja", "Petrochemical Refinery"),
}

# Plain-language explanation templates by tamper type
TAMPER_EXPLANATIONS = {
    "T1": {
        "label": "T1 — Constant Value / Flatline",
        "category": "Sensor Output Invariance / Freezing",
        "observed": "Sensor readings remained invariant over {duration_hours}h ({duration_rows} consecutive 15-minute intervals).",
        "why_flagged": "Causal rolling standard deviation fell to zero while expanding past MAD indicated natural variation in effluent stream.",
        "possible_explanations": "Sensor diaphragm fouling, transmitter digital lockup, offline state hold, or intentional signal clamping.",
        "recommended_checks": [
            "Check live analog loop current (4-20mA) at transmitter terminals.",
            "Verify OCEMS maintenance and automated sensor wash logs.",
            "Cross-reference flow meter readings during the flagged period."
        ]
    },
    "T2": {
        "label": "T2 — Replayed Window / Copy-Paste",
        "category": "Historical Telemetry Replay",
        "observed": "A repeated sequence of readings spanning {duration_hours}h matched previously logged telemetry.",
        "why_flagged": "Lagged autocorrelation and similarity indices over windows 96–672 rows exceeded stochastic limits.",
        "possible_explanations": "Telemetry buffer replay glitch in RTU data logger, SCADA buffering loop, or automated replay of compliant past data.",
        "recommended_checks": [
            "Inspect raw transmission packet timestamps and serial transmission counter.",
            "Verify physical discharge against wastewater treatment plant electricity draw.",
            "Review SCADA data logger audit trail for replay loops."
        ]
    },
    "T3": {
        "label": "T3 — CTO Limit Hugging",
        "category": "Consent to Operate (CTO) Threshold Hugging",
        "observed": "Effluent readings remained confined within a tight band immediately below the regulatory consent limit over {duration_hours}h.",
        "why_flagged": "Abnormal concentration of readings between 85% and 99% of consent threshold with suppressed upper-tail excursions.",
        "possible_explanations": "Tight automated dosing control, electronic signal ceiling/clipping, or calibration span compression.",
        "recommended_checks": [
            "Conduct grab sample laboratory analysis at discharge outlet weir.",
            "Inspect automated dosing pump PID controller configuration and log files.",
            "Verify calibration span settings on the online analyzer."
        ]
    },
    "T7": {
        "label": "T7 — Systematic Baseline Drift / Shift",
        "category": "Systematic Baseline Level Shift",
        "observed": "An abrupt level shift or sustained downward trend occurred over {duration_hours}h relative to prior 7-day operating baseline.",
        "why_flagged": "Causal level shift and slope statistics deviated significantly from prior 672-row baseline (>3 standard deviations).",
        "possible_explanations": "Process reduction, genuine effluent treatment improvement, analyzer zero-point drift, dilution water ingress, or manual span adjustment.",
        "recommended_checks": [
            "Correlate flagged period with industrial production logs and chemical consumption.",
            "Verify water intake meter readings to rule out effluent dilution.",
            "Inspect online analyzer calibration logs for undocumented zero adjustments."
        ]
    }
}


class V2BackendAdapter:
    """Singleton adapter to serve verified V2 evaluation artifacts to backend endpoints."""

    def __init__(self):
        self._events_df: Optional[pd.DataFrame] = None
        self._clean_fa_df: Optional[pd.DataFrame] = None
        self._methods_df: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self):
        if os.path.exists(V2_EVAL_EVENTS_CSV):
            self._events_df = pd.read_csv(V2_EVAL_EVENTS_CSV)
        if os.path.exists(V2_CLEAN_FA_CSV):
            self._clean_fa_df = pd.read_csv(V2_CLEAN_FA_CSV)
        if os.path.exists(V2_METHODS_CSV):
            self._methods_df = pd.read_csv(V2_METHODS_CSV)

    @property
    def is_available(self) -> bool:
        return self._events_df is not None and not self._events_df.empty

    def get_model_info(self) -> Dict[str, Any]:
        """Returns verified V2 model architecture, feature specifications, and reconciled metrics."""
        return {
            "model_name": "ForensiAIR V2 Causal Supervised Detector",
            "model_version": "2.0.0-frozen",
            "specification": "docs/PROTOCOL_v2.md & PROTOCOL_v1.1 Section C",
            "architecture": "HistGradientBoostingClassifier (max_depth=6, lr=0.1, max_iter=200, l2=1.0, balanced class weights, random_state=42)",
            "feature_engineering": {
                "feature_count": 45,
                "window_sizes": [16, 48, 96, 288],  # 4h, 12h, 24h, 72h
                "past_only_causal": True,
                "normalization": "Expanding past Median Absolute Deviation (MAD), strictly past-only",
                "features": [
                    "Rolling range (w=16, 48, 96, 288)",
                    "Rolling std dev (w=16, 48, 96, 288)",
                    "Exact-repeat run length",
                    "Unique value count (w=16, 48, 96, 288)",
                    "Unchanged fraction (w=16, 48, 96, 288)",
                    "Level shift vs prior 672 rows (7 days)",
                    "Slope vs prior 672 rows",
                    "Minimum lagged similarity over lags 96-672 (scaled by MAD)",
                    "Limit ratio and fraction above 85% of CTO limit",
                    "Missing fraction (w=16, 48, 96, 288)"
                ]
            },
            "operating_budget": {
                "target": "1.0 false alert episode per factory-month",
                "direction_1_tau": 0.97875,
                "direction_2_tau": 0.96469,
                "realized_clean_episodes": 328,
                "total_exposure_months": 327.61,
                "episode_merging_gap": "<= 16 rows (4.0 hours)",
                "missing_data_safety": "Missing values (value=NaN) produce score=NaN; IEEE 754 float comparison evaluates (NaN >= tau) to False, preventing missing readings from starting or continuing alerts.",
                "production_calibration_notice": (
                    "The 1.0 alert/factory-month false-alarm rate was calibrated on 33 development factories "
                    "under frozen protocol constraints. This is a development operating benchmark and does not "
                    "constitute an empirical guarantee for unseen production data."
                )
            },
            "reconciliation_statement": (
                "Metric Reconciliation: The preliminary 14.68% figure reflected the frozen V1 baseline on all 2,698 raw Mechanism B "
                "events prior to no-op exclusion (396/2,698). Under the protocol-frozen post-hoc evaluation on primary non-no-op "
                "events, the verified V2 pooled recall at 1.0 alert/month is 17.31% (Direction 1: Train A -> Test B, N=2,553) "
                "and 30.60% (Direction 2: Train B -> Test A, N=1,899). V1 M1 baseline recall on the same events is 15.39% and 10.16%."
            ),
            "reconciled_metrics": {
                "direction_1_cross_mechanism": {
                    "training_set": "Mechanism A (seeds 1-5)",
                    "test_set": "Mechanism B (seeds 301-305)",
                    "evaluated_events": 2553,
                    "v2_pooled_recall": 0.1731,
                    "v2_ci_95": [0.1181, 0.2292],
                    "v1_m1_pooled_recall": 0.1539,
                    "v1_m1_ci_95": [0.1058, 0.2037],
                    "paired_diff_v2_minus_v1": 0.0192,
                    "paired_ci_95": [-0.0333, 0.0692],
                    "is_statistically_significant": False,
                    "recall_by_type": {
                        "T1_flatline": {"v2": 0.0798, "v1_m1": 0.1275, "events": 714},
                        "T2_copy_paste": {"v2": 0.3294, "v1_m1": 0.0843, "events": 510},
                        "T3_limit_hugging": {"v2": 0.0442, "v1_m1": 0.1980, "events": 611},
                        "T7_drift": {"v2": 0.2646, "v1_m1": 0.1922, "events": 718}
                    }
                },
                "direction_2_cross_mechanism": {
                    "training_set": "Mechanism B (seeds 301-305)",
                    "test_set": "Mechanism A (seeds 1-5)",
                    "evaluated_events": 1899,
                    "v2_pooled_recall": 0.3060,
                    "v2_ci_95": [0.2297, 0.3745],
                    "v1_m1_pooled_recall": 0.1016,
                    "v1_m1_ci_95": [0.0669, 0.1390],
                    "paired_diff_v2_minus_v1": 0.2043,
                    "paired_ci_95": [0.1299, 0.2729],
                    "is_statistically_significant": True,
                    "recall_by_type": {
                        "T1_flatline": {"v2": 0.1807, "v1_m1": 0.1623, "events": 653},
                        "T2_copy_paste": {"v2": 0.3436, "v1_m1": 0.0710, "events": 521},
                        "T3_limit_hugging": {"v2": 0.3739, "v1_m1": 0.0340, "events": 353},
                        "T7_drift": {"v2": 0.4086, "v1_m1": 0.1022, "events": 372}
                    }
                }
            },
            "inference_mode": "Historical Development Evaluation (5-Fold Factory-Grouped Cross-Mechanism LOFO)",
            "is_live_inference": False,
            "data_source": "validation_v2/v2/model/v2_eval_events.csv",
            "disclaimer": MANDATORY_V2_DISCLAIMER
        }

    def get_alerts(
        self,
        factory_id: Optional[str] = None,
        tamper_type: Optional[str] = None,
        severity: Optional[str] = None,
        direction: str = "dir1",
        detected_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Returns validated V2 alert episodes from historical evaluation outputs.
        """
        if not self.is_available:
            return {
                "alerts": [],
                "total": 0,
                "is_live_inference": False,
                "data_source": "none",
                "disclaimer": MANDATORY_V2_DISCLAIMER
            }

        df = self._events_df.copy()

        # Exclude no-op events
        if "no_op" in df.columns:
            df = df[df["no_op"] == False]

        det_col = f"is_detected_{direction}_pooled" if f"is_detected_{direction}_pooled" in df.columns else "is_detected_dir1_pooled"
        delay_col = f"delay_{direction}_pooled" if f"delay_{direction}_pooled" in df.columns else "delay_dir1_pooled"

        if detected_only and det_col in df.columns:
            df = df[df[det_col] == True]

        if factory_id:
            df = df[df["factory_id"] == factory_id]

        if tamper_type:
            df = df[df["type"] == tamper_type.upper()]

        if severity:
            df = df[df["severity"] == severity.lower()]

        total_matching = len(df)
        df_page = df.iloc[offset: offset + limit]

        alerts = []
        for _, row in df_page.iterrows():
            fid = str(row["factory_id"])
            name, reg, ind = FACTORY_NAMES.get(fid, (f"Industrial Facility {fid}", "Taloja", "Chemical Manufacturing"))
            ttype = str(row["type"])
            dur_rows = int(row.get("duration_rows", 16))
            dur_hours = round(dur_rows * 0.25, 2)

            expl = TAMPER_EXPLANATIONS.get(ttype, TAMPER_EXPLANATIONS["T1"])
            delay_val = row.get(delay_col)
            delay_hours = round(float(delay_val), 2) if pd.notna(delay_val) else None

            alerts.append({
                "alert_id": str(row["event_id"]),
                "factory_id": fid,
                "factory_name": name,
                "region": reg,
                "industry": ind,
                "parameter": str(row["parameter"]),
                "tamper_type": ttype,
                "tamper_label": expl["label"],
                "anomaly_category": expl["category"],
                "severity": str(row.get("severity", "moderate")),
                "start_time": str(row["start_dt"]),
                "end_time": str(row["end_dt"]),
                "duration_rows": dur_rows,
                "duration_hours": dur_hours,
                "mechanism": f"Mechanism {row.get('mechanism', 'B')}",
                "seed": int(row.get("seed", 301)),
                "detected_by_v2": bool(row.get(det_col, False)),
                "detection_delay_hours": delay_hours,
                "detected_by_v1_m1": bool(row.get("is_detected_V1_M1", False)),
                "detected_by_v1_if": bool(row.get("is_detected_V1_IF", False)),
                "detected_by_baseline_b0": bool(row.get("is_detected_B0", False)),
                "evidence": {
                    "observed": expl["observed"].format(duration_hours=dur_hours, duration_rows=dur_rows),
                    "why_flagged": expl["why_flagged"],
                    "possible_explanations": expl["possible_explanations"],
                    "recommended_checks": expl["recommended_checks"]
                },
                "is_live_inference": False,
                "data_source": "historical_development_evaluation"
            })

        return {
            "alerts": alerts,
            "total": total_matching,
            "limit": limit,
            "offset": offset,
            "operating_budget_context": {
                "target_budget": "1.0 false alert episode per factory-month",
                "operating_tau": 0.97875 if direction == "dir1" else 0.96469,
                "direction": direction,
                "realized_clean_episodes": 328
            },
            "is_live_inference": False,
            "data_source": "validation_v2/v2/model/v2_eval_events.csv",
            "disclaimer": MANDATORY_V2_DISCLAIMER
        }

    def get_factory_analysis(self, factory_id: str) -> Dict[str, Any]:
        """
        Returns factory-specific V2 performance, clean false-alarm rate, and event detection summary.
        """
        if factory_id not in FACTORY_NAMES:
            return {
                "found": False,
                "error": f"Factory {factory_id} not found among the 33 development factories."
            }

        name, reg, ind = FACTORY_NAMES[factory_id]

        # Exposure and clean false alarms
        exposure_months = 12.02
        clean_fa_count = 0
        clean_fa_rate = 0.0

        if self._clean_fa_df is not None and not self._clean_fa_df.empty:
            sub_fa = self._clean_fa_df[(self._clean_fa_df["Direction"] == "dir1") &
                                       (self._clean_fa_df["Model"] == "pooled") &
                                       (self._clean_fa_df["Factory_ID"] == factory_id)]
            if not sub_fa.empty:
                r_fa = sub_fa.iloc[0]
                exposure_months = float(r_fa.get("Exposure_Months", 12.02))
                clean_fa_count = int(r_fa.get("Alert_Episodes", 0))
                clean_fa_rate = float(r_fa.get("FA_Rate_mo", 0.0))

        # Injected event performance for this factory
        events_evaluated = 0
        v2_detected = 0
        v1_detected = 0
        type_breakdown = {}

        recent_episodes = []
        if self._events_df is not None and not self._events_df.empty:
            fac_events = self._events_df[(self._events_df["factory_id"] == factory_id) &
                                          (self._events_df["no_op"] == False)].copy()
            events_evaluated = len(fac_events)
            if events_evaluated > 0:
                v2_detected = int(fac_events["is_detected_dir1_pooled"].sum())
                v1_detected = int(fac_events["is_detected_V1_M1"].sum())

                for t, grp in fac_events.groupby("type"):
                    type_breakdown[t] = {
                        "total_events": int(len(grp)),
                        "v2_detected": int(grp["is_detected_dir1_pooled"].sum()),
                        "v2_recall": round(float(grp["is_detected_dir1_pooled"].mean()), 4),
                        "v1_detected": int(grp["is_detected_V1_M1"].sum()),
                        "v1_recall": round(float(grp["is_detected_V1_M1"].mean()), 4)
                    }

                # Top 10 detected episodes
                det_sub = fac_events[fac_events["is_detected_dir1_pooled"] == True].head(10)
                for _, r in det_sub.iterrows():
                    ttype = str(r["type"])
                    dur_rows = int(r.get("duration_rows", 16))
                    dur_hours = round(dur_rows * 0.25, 2)
                    expl = TAMPER_EXPLANATIONS.get(ttype, TAMPER_EXPLANATIONS["T1"])
                    recent_episodes.append({
                        "event_id": str(r["event_id"]),
                        "parameter": str(r["parameter"]),
                        "tamper_type": ttype,
                        "anomaly_category": expl["category"],
                        "severity": str(r.get("severity", "moderate")),
                        "start_time": str(r["start_dt"]),
                        "end_time": str(r["end_dt"]),
                        "duration_hours": dur_hours,
                        "mechanism": f"Mechanism {r.get('mechanism', 'B')}"
                    })

        v2_recall = round(v2_detected / events_evaluated, 4) if events_evaluated > 0 else 0.0
        v1_recall = round(v1_detected / events_evaluated, 4) if events_evaluated > 0 else 0.0

        return {
            "found": True,
            "factory_id": factory_id,
            "factory_name": name,
            "region": reg,
            "industry": ind,
            "exposure_months": exposure_months,
            "clean_false_alarm_episodes": clean_fa_count,
            "clean_false_alarm_rate_per_month": clean_fa_rate,
            "target_false_alarm_budget": "1.0 / factory-month",
            "evaluation_metrics": {
                "events_evaluated": events_evaluated,
                "v2_detected_events": v2_detected,
                "v2_recall": v2_recall,
                "v1_m1_detected_events": v1_detected,
                "v1_m1_recall": v1_recall,
                "paired_improvement": round(v2_recall - v1_recall, 4),
                "type_breakdown": type_breakdown
            },
            "recent_detected_episodes": recent_episodes,
            "is_live_inference": False,
            "data_source": "historical_development_evaluation",
            "operating_tau": 0.97875,
            "plain_language_summary": (
                f"Facility {name} was evaluated across {exposure_months:.1f} factory-months of telemetry. "
                f"On clean un-injected telemetry, V2 triggered {clean_fa_count} false-alarm episodes ({clean_fa_rate:.2f}/month). "
                f"Across {events_evaluated} synthetic test anomaly injections, V2 achieved {v2_recall * 100:.1f}% recall "
                f"compared to {v1_recall * 100:.1f}% for the frozen V1 baseline."
            ),
            "disclaimer": MANDATORY_V2_DISCLAIMER
        }


# Singleton instance
_v2_adapter_instance = None


def get_v2_adapter() -> V2BackendAdapter:
    global _v2_adapter_instance
    if _v2_adapter_instance is None:
        _v2_adapter_instance = V2BackendAdapter()
    return _v2_adapter_instance
