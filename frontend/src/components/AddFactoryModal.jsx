import React, { useState } from 'react';
import { apiFetch } from '../config';

export function AddFactoryModal({ isOpen, onClose, onFactoryAdded }) {
  const [name, setName] = useState('');
  const [district, setDistrict] = useState('Northern Industrial Zone');
  const [industryType, setIndustryType] = useState('Chemical Manufacturing');
  const [complianceStatus, setComplianceStatus] = useState('Compliant');
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    setSubmitting(true);
    try {
      const res = await apiFetch(`/api/admin/factories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          district,
          industry_type: industryType,
          compliance_status: complianceStatus
        })
      });

      if (res.ok) {
        const json = await res.json();
        onFactoryAdded(json.factory);
        onClose();
        setName('');
      } else {
        alert(`Failed to add factory. Server responded with ${res.status}.`);
      }
    } catch (err) {
      console.error("Error creating factory:", err);
      alert("Failed to add factory -- couldn't reach the backend. Nothing was saved.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">+ Add New Factory</div>
          <button className="icon-btn" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label>Factory / Industrial Facility Name</label>
              <input 
                type="text" 
                placeholder="e.g. BlueWave Chemicals Ltd." 
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>District / Sector Location</label>
              <select value={district} onChange={(e) => setDistrict(e.target.value)}>
                <option value="Northern Industrial Zone">Northern Industrial Zone</option>
                <option value="Coastal Sector">Coastal Sector</option>
                <option value="Urban Fringe">Urban Fringe</option>
                <option value="MIDC Tarapur">MIDC Tarapur</option>
                <option value="MIDC Taloja">MIDC Taloja</option>
              </select>
            </div>

            <div className="form-group">
              <label>Industry Type Category</label>
              <select value={industryType} onChange={(e) => setIndustryType(e.target.value)}>
                <option value="Chemical Manufacturing">Chemical Manufacturing</option>
                <option value="Heavy Metallurgy">Heavy Metallurgy</option>
                <option value="Garment & Dyeing">Garment & Dyeing</option>
                <option value="Synthetic Rubber">Synthetic Rubber</option>
                <option value="Pulp & Paper">Pulp & Paper</option>
                <option value="Glass Manufacturing">Glass Manufacturing</option>
                <option value="Construction Materials">Construction Materials</option>
              </select>
            </div>

            <div className="form-group">
              <label>Initial Compliance Status</label>
              <select value={complianceStatus} onChange={(e) => setComplianceStatus(e.target.value)}>
                <option value="Compliant">Compliant</option>
                <option value="Under Review">Under Review</option>
                <option value="Critical Breach">Critical Breach</option>
              </select>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Registering...' : 'Add Factory'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
