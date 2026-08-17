from typing import Dict, Any

# QC FIX (2026-08): these two constants convert the Isolation Forest's raw
# score_samples() output into a 0-1 "how anomalous is this" number. They used
# to be guessed (0.2 / 0.4) and didn't match the model's real output range at
# all -- verified that produced iso_score_norm = 1.0 (max) for 100% of
# readings, real and synthetic, meaning this term never actually varied.
#
# These replacements are calibrated from the actual trained Isolation
# Forest's score_samples() distribution on real telemetry:
#   ISO_SCORE_NORMAL_ANCHOR = 75th percentile of real scores (-0.342)
#     -> readings at or above "typical" map to 0 (not anomalous)
#   ISO_SCORE_ANOMALOUS_ANCHOR = 1st percentile of real scores (-0.627)
#     -> readings at the extreme low tail map to 1 (fully anomalous)
# Readings between the two anchors scale linearly.
#
# NOTE: if iso_forest.joblib is ever retrained, these two anchors should be
# recomputed against the new model's score distribution -- they are specific
# to the current model, not a universal constant.
ISO_SCORE_NORMAL_ANCHOR = -0.342
ISO_SCORE_ANOMALOUS_ANCHOR = -0.627


def calculate_composite_risk(
    xgb_prob: float,
    iso_anomaly_score: float,
    fingerprint_triggers: Dict[str, Any]
) -> Dict[str, Any]:
    """
    fingerprint_triggers must contain already-decided 0/1 (or True/False)
    values per fingerprint -- e.g. from fingerprint_engine.py's trig_* columns
    -- NOT the raw magnitude/percentage/z-score values. Each fingerprint type
    is on its own scale (a percentage, a z-score, a percent difference) and
    this function has no way to know the right threshold for each one; that
    thresholding must happen upstream, once, where the meaning of each value
    is actually known.
    """
    iso_span = ISO_SCORE_NORMAL_ANCHOR - ISO_SCORE_ANOMALOUS_ANCHOR
    iso_score_norm = max(0.0, min(
        1.0,
        (ISO_SCORE_NORMAL_ANCHOR - iso_anomaly_score) / iso_span
    ))

    triggered_count = 0
    total_fingerprints = 8
    fingerprint_keys = [
        'impossible_ph_range', 'inspection_dip', 'flatline', 'limit_hugging',
        'correlation_break', 'copy_paste', 'coordinated_missing_data',
        'data_integrity'
    ]

    triggered_names = []
    for fp in fingerprint_keys:
        val = fingerprint_triggers.get(fp, 0)
        if bool(val):
            triggered_count += 1
            triggered_names.append(fp.replace('_', ' ').title())

    fp_ratio = triggered_count / total_fingerprints
    composite = (0.45 * xgb_prob) + (0.25 * iso_score_norm) + (0.30 * fp_ratio)
    risk_score = round(composite * 100, 1)
    
    if risk_score >= 75 or triggered_count >= 4:
        category = "CRITICAL"
        action = "Immediate unannounced physical site inspection & automated regulator dispatch."
    elif risk_score >= 50 or triggered_count >= 2:
        category = "HIGH"
        action = "Issue formal notice of telemetry anomaly & schedule audit within 48 hours."
    elif risk_score >= 25 or triggered_count >= 1:
        category = "MEDIUM"
        action = "Flag site for heightened monitoring & mandate sensor calibration report."
    else:
        category = "LOW"
        action = "Normal routine surveillance."
        
    return {
        "risk_score": risk_score,
        "risk_category": category,
        "recommended_action": action,
        "xgb_probability": round(xgb_prob, 4),
        "anomaly_score": round(iso_score_norm, 4),
        "triggered_fingerprints": triggered_names,
        "total_fingerprints_triggered": triggered_count
    }
