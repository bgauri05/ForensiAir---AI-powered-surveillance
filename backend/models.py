from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Factory(Base):
    __tablename__ = "factories"
    
    factory_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    industry_type = Column(String, default="Chemical Manufacturing")
    location = Column(String, default="Maharashtra Industrial Zone")
    total_fingerprints_triggered = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)
    risk_category = Column(String, default="LOW")
    # QC FIX (2026-08): these two are the actual model outputs that feed
    # calculate_composite_risk() -- persisted here so the live API can read
    # a factory's real tamper probability / anomaly score straight from the
    # database instead of re-running inference on every request, or (worse)
    # falling back to a separately-guessed formula.
    xgb_probability = Column(Float, default=0.0)
    anomaly_score_norm = Column(Float, default=0.0)
    status = Column(String, default="Active")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    fingerprints = relationship("FingerprintScore", uselist=False, back_populates="factory")
    inspections = relationship("InspectionEvent", back_populates="factory")
    alerts = relationship("Alert", back_populates="factory")

class FingerprintScore(Base):
    __tablename__ = "fingerprint_scores"
    
    factory_id = Column(String, ForeignKey("factories.factory_id"), primary_key=True)
    impossible_ph_range = Column(Float, default=0.0)
    inspection_dip = Column(Float, default=0.0)
    flatline = Column(Float, default=0.0)
    limit_hugging = Column(Float, default=0.0)
    correlation_break = Column(Float, default=0.0)
    copy_paste = Column(Float, default=0.0)
    coordinated_missing_data = Column(Float, default=0.0)
    data_integrity = Column(Float, default=0.0)
    # QC FIX (2026-08): the raw magnitudes above are on different scales
    # (percentages, z-scores) with no shared "is this triggered" meaning --
    # these are the actual 0/1 trigger decisions from fingerprint_engine.py,
    # persisted so downstream readers don't have to re-guess a threshold.
    trig_impossible_ph_range = Column(Integer, default=0)
    trig_inspection_dip = Column(Integer, default=0)
    trig_flatline = Column(Integer, default=0)
    trig_limit_hugging = Column(Integer, default=0)
    trig_correlation_break = Column(Integer, default=0)
    trig_copy_paste = Column(Integer, default=0)
    trig_coordinated_missing_data = Column(Integer, default=0)
    trig_data_integrity = Column(Integer, default=0)
    total_fingerprints_triggered = Column(Integer, default=0)
    
    factory = relationship("Factory", back_populates="fingerprints")

class InspectionEvent(Base):
    __tablename__ = "inspection_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    factory_id = Column(String, ForeignKey("factories.factory_id"), index=True)
    inspection_date = Column(String)
    inspection_type = Column(String)
    status = Column(String)
    notes = Column(Text, nullable=True)
    
    factory = relationship("Factory", back_populates="inspections")

class TelemetryRecord(Base):
    __tablename__ = "telemetry"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    factory_id = Column(String, index=True)
    parameter_id = Column(String, index=True)
    timestamp = Column(String, index=True)
    value = Column(Float)
    rolling_mean = Column(Float, nullable=True)
    rolling_std = Column(Float, nullable=True)
    flatline_flag = Column(Float, nullable=True)
    limit_hugging = Column(Float, nullable=True)
    autocorrelation = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    factory_id = Column(String, ForeignKey("factories.factory_id"), index=True)
    alert_type = Column(String)
    severity = Column(String)
    message = Column(String)
    timestamp = Column(String)
    status = Column(String, default="OPEN")
    
    factory = relationship("Factory", back_populates="alerts")

class ConsentLimit(Base):
    __tablename__ = "consent_limits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_id = Column(String, unique=True, index=True)
    parameter_name = Column(String)
    unit = Column(String)
    min_limit = Column(Float, nullable=True)
    max_limit = Column(Float, nullable=True)
    regulatory_standard = Column(String, default="CPCB Standard 2024")
    category = Column(String, default="Effluent Quality")

class SystemThreshold(Base):
    __tablename__ = "system_thresholds"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String, unique=True, index=True)
    setting_name = Column(String)
    value = Column(Float)
    unit = Column(String)
    description = Column(String)

class UserAccess(Base):
    __tablename__ = "user_access"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    email = Column(String, unique=True)
    role = Column(String)
    district_access = Column(String)
    status = Column(String, default="Active")
    last_login = Column(String)

