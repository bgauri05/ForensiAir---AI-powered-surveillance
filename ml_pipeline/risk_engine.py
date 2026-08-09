from typing import Dict, Any

def calculate_composite_risk(
    xgb_prob: float,
    iso_anomaly_score: float,
    fingerprint_triggers: Dict[str, Any]
) -> Dict[str, Any]:
    iso_score_norm = max(0.0, min(1.0, (0.2 - iso_anomaly_score) / 0.4))
    
    triggered_count = 0
    total_fingerprints = 7
    fingerprint_keys = [
        'impossible_ph_range', 'inspection_dip', 'flatline', 'limit_hugging',
        'correlation_break', 'copy_paste', 'coordinated_missing_data'
    ]
    
    triggered_names = []
    for fp in fingerprint_keys:
        val = fingerprint_triggers.get(fp, 0)
        if isinstance(val, (int, float)) and val > 0:
            triggered_count += 1
            triggered_names.append(fp.replace('_', ' ').title())
        elif isinstance(val, bool) and val:
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
