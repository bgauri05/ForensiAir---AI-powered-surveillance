import pdfplumber
import re
import os
import json
from collector.consent.logger import logger

# List of parameter keywords to detect dynamically
PARAMETER_KEYWORDS = [
    "ph", "bod", "cod", "tss", "tds", "oil & grease", "oil and grease", "sulphate", "chloride",
    "phosphate", "suspended solids", "dissolved solids", "so2", "nox", "particulate matter",
    "spm", "tpm", "ammoniacal nitrogen", "nh3-n", "toc", "temperature", "flow", "quantity of sewage",
    "trade effluent", "chlorides", "sulphates", "suspended", "dissolved", "ammonia"
]

def clean_text(val):
    if val is None:
        return ""
    return " ".join(str(val).split()).strip()

def parse_date(date_str):
    if not date_str:
        return None
    # Support formats: DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY
    match = re.search(r'(\d{2})[-/\.](\d{2})[-/\.](\d{4})', date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    return None

def parse_limit_values(std_str):
    std_str = std_str.lower().replace(",", "").strip()
    
    # 1. Range (e.g., "5.5 - 9.0" or "5.5 to 9.0")
    range_match = re.search(r'([\d\.]+)\s*(?:to|-)\s*([\d\.]+)', std_str)
    if range_match:
        try:
            return float(range_match.group(1)), float(range_match.group(2))
        except ValueError:
            pass
            
    # 2. Single numeric value (e.g., "<= 250", "not to exceed 100", "100")
    num_match = re.findall(r'[\d\.]+', std_str)
    if num_match:
        try:
            val = float(num_match[0])
            return None, val
        except ValueError:
            pass
            
    return None, None

def parse_unit(text):
    text = text.lower()
    if re.search(r'mg/\s*nm[3³]', text):
        return "mg/Nm3"
    if re.search(r'mg/\s*l', text):
        return "mg/l"
    if "ph" in text:
        return "pH"
    if "kld" in text:
        return "KLD"
    if "ppm" in text:
        return "ppm"
    if re.search(r'kg/\s*day', text):
        return "kg/day"
    return None

def parse_cto_metadata(pdf_path):
    """
    Extract issue date, validity, and type from CTO text.
    """
    metadata = {
        "consent_type": None,
        "issue_date": None,
        "valid_from": None,
        "valid_until": None,
        "industry": None
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:3]: # Usually in the first 2-3 pages
                text += page.extract_text() or ""
                
            # Clean text
            clean_t = clean_text(text)
            
            # Extract consent type
            type_match = re.search(r'(consent to operate|consent to establish|consent to renewal|cto|cte|renewal of consent)', clean_t, re.IGNORECASE)
            if type_match:
                metadata["consent_type"] = type_match.group(1).title()
            else:
                metadata["consent_type"] = "Consent to Operate"
                
            # Extract issue date
            issue_match = re.search(r'(?:date|dated|issue date)[:\s]+(\d{2}[-/\.]\d{2}[-/\.]\d{4})', clean_t, re.IGNORECASE)
            if issue_match:
                metadata["issue_date"] = parse_date(issue_match.group(1))
                
            # Extract validity dates
            # E.g. "valid from 01/01/2024 to 31/12/2024" or "valid up to 31/12/2024"
            valid_from_match = re.search(r'valid\s+from\s+(\d{2}[-/\.]\d{2}[-/\.]\d{4})', clean_t, re.IGNORECASE)
            if valid_from_match:
                metadata["valid_from"] = parse_date(valid_from_match.group(1))
                
            valid_until_match = re.search(r'valid\s+(?:up\s+to|upto|to|till|until)\s+(\d{2}[-/\.]\d{2}[-/\.]\d{4})', clean_t, re.IGNORECASE)
            if valid_until_match:
                metadata["valid_until"] = parse_date(valid_until_match.group(1))
            else:
                # Search for any date at the end of the first page text which often represents validity
                dates = re.findall(r'(\d{2}[-/\.]\d{2}[-/\.]\d{4})', clean_t[:2000])
                if len(dates) >= 2:
                    metadata["valid_until"] = parse_date(dates[-1])
                    if not metadata["valid_from"]:
                        metadata["valid_from"] = parse_date(dates[0])
                        
            # If valid_from is still empty but valid_until is present, set valid_from to issue_date or 5 years prior
            if not metadata["valid_from"] and metadata["issue_date"]:
                metadata["valid_from"] = metadata["issue_date"]
                
    except Exception as e:
        logger.error(f"Failed to parse CTO metadata: {e}")
        
    return metadata

def parse_cto_limits(pdf_path, factory_id):
    """
    Extract dynamic environmental parameter limits from tables.
    """
    limits = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                tables = page.extract_tables() or []
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue
                        
                    # Clean and clean cells
                    cleaned_table = []
                    for r in table:
                        cleaned_table.append([clean_text(cell) for cell in r])
                        
                    # Let's check if this is a parameters table
                    is_param_table = False
                    for row in cleaned_table:
                        for cell in row:
                            cell_lower = cell.lower()
                            if any(kw == cell_lower or f" {kw} " in f" {cell_lower} " for kw in PARAMETER_KEYWORDS):
                                is_param_table = True
                                break
                        if is_param_table:
                            break
                            
                    if not is_param_table:
                        continue
                        
                    logger.info(f"Processing parameter table at Page {page_idx+1}, Table {table_idx+1}")
                    
                    # Parse rows
                    for row_idx, row in enumerate(cleaned_table):
                        # Find the cell containing the parameter name
                        param_cell_idx = -1
                        param_name = ""
                        for cell_idx, cell in enumerate(row):
                            cell_lower = cell.lower()
                            # Match exactly or as a token
                            if any(kw == cell_lower or f" {kw} " in f" {cell_lower} " for kw in PARAMETER_KEYWORDS):
                                # Skip header row matching keywords (e.g. "Parameter" header itself!)
                                if cell_lower in {"parameter", "parameters", "parameters/standards"}:
                                    continue
                                param_cell_idx = cell_idx
                                param_name = cell
                                break
                                
                        if param_cell_idx == -1:
                            continue
                            
                        # Look at other cells in the same row for standards / values
                        min_val, max_val = None, None
                        unit = None
                        condition_text = ""
                        
                        # Inspect other cells in the row
                        for cell_idx, cell in enumerate(row):
                            if cell_idx == param_cell_idx or not cell:
                                continue
                            
                            # Check if cell has numbers
                            if any(c.isdigit() for c in cell):
                                cur_min, cur_max = parse_limit_values(cell)
                                if cur_min is not None:
                                    min_val = cur_min
                                if cur_max is not None:
                                    max_val = cur_max
                                    
                                condition_text = cell
                                
                            # Check for unit
                            cur_unit = parse_unit(cell)
                            if cur_unit:
                                unit = cur_unit
                                
                        # Fallback: if no unit was extracted, check parameter cell text
                        if not unit:
                            unit = parse_unit(param_name)
                            
                        # If we extracted at least one limit value, save the limit record
                        if min_val is not None or max_val is not None:
                            limits.append({
                                "factory_id": factory_id,
                                "parameter": param_name,
                                "minimum_limit": min_val,
                                "maximum_limit": max_val,
                                "unit": unit or "mg/l" if "so2" not in param_name.lower() and "nox" not in param_name.lower() else "mg/Nm3",
                                "condition_text": condition_text,
                                "page_number": page_idx + 1,
                                "table_number": table_idx + 1,
                                "extraction_confidence": 0.95
                            })
                            
    except Exception as e:
        logger.error(f"Error parsing PDF limits: {e}")
        
    return limits
