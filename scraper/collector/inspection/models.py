from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any

@dataclass
class InspectionRecord:
    factory_name: str
    inspection_date: date
    inspection_type: str
    region: Optional[str] = None
    district: Optional[str] = None
    midc: Optional[str] = None
    officer_name: Optional[str] = None
    status: Optional[str] = "Scheduled"
    remarks: Optional[str] = None
    address: Optional[str] = None
    inspection_dept: Optional[str] = None
    contact_details: Optional[str] = None
    source_url: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass fields to dict for insertion."""
        return {
            "factory_name": self.factory_name,
            "inspection_date": self.inspection_date,
            "inspection_type": self.inspection_type,
            "region": self.region,
            "district": self.district,
            "midc": self.midc,
            "officer_name": self.officer_name,
            "status": self.status,
            "remarks": self.remarks,
            "address": self.address,
            "inspection_dept": self.inspection_dept,
            "contact_details": self.contact_details,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at
        }
