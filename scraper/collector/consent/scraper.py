import requests
import urllib3
import re
import time
import os
import ddddocr
import sys
from bs4 import BeautifulSoup
from urllib3.util import connection
from collector.consent.config import CMS_BASE_URL, CMS_IP_PATCH, REQUEST_TIMEOUT, MAX_CAPTCHA_RETRIES
from collector.consent.logger import logger

# Reconfigure stdout to UTF-8 to prevent ddddocr startup print errors on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Urllib3 Connection override to patch www.ecmpcb.in
_orig_create_connection = connection.create_connection

def patched_create_connection(address, *args, **kwargs):
    host, port = address
    if host == "www.ecmpcb.in":
        # Override to Direct IP
        return _orig_create_connection((CMS_IP_PATCH, port), *args, **kwargs)
    return _orig_create_connection(address, *args, **kwargs)

connection.create_connection = patched_create_connection
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    })
    return session

def solve_captcha(session, captcha_url):
    try:
        resp = session.get(captcha_url, verify=False, timeout=10)
        resp.raise_for_status()
        ocr = ddddocr.DdddOcr(show_ad=False)
        code = ocr.classification(resp.content)
        # Strip any spaces or noise characters
        return str(code or "").strip()
    except Exception as e:
        logger.error(f"Failed to solve captcha: {e}")
        return ""

def is_valid_captcha(code):
    import string
    if len(code) != 4:
        return False
    allowed = string.ascii_letters + string.digits
    return all(c in allowed for c in code)

def query_cms_for_consent(consent_number):
    """
    Search MPCB portal live using captcha solver.
    Returns (blockchain_doc_url, consent_metadata) or (None, None).
    """
    session = get_session()
    
    # We will try up to 30 attempts to solve the captcha
    max_total_attempts = 30
    attempt = 0
    
    while attempt < max_total_attempts:
        attempt += 1
        try:
            logger.info(f"[{consent_number}] live query attempt {attempt}...")
            # Load search portal page
            resp = session.get(CMS_BASE_URL, verify=False, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "html.parser")
            img = soup.find("img", src=lambda s: s and "captcha" in s)
            if not img:
                logger.error("No captcha image found on CMS page.")
                time.sleep(1.0)
                continue
                
            captcha_url = img.get("src")
            captcha_code = solve_captcha(session, captcha_url)
            if not captcha_code:
                time.sleep(1.0)
                continue
                
            # Clean and validate captcha locally first
            captcha_code = captcha_code.strip()
            if not is_valid_captcha(captcha_code):
                logger.info(f"[{consent_number}] Captcha solve '{captcha_code}' is invalid format. Retrying locally...")
                # We do not hit the search page with invalid captcha to avoid server-side noise/blocks
                continue
                
            # Submit search request
            params = {
                "search_by_name": consent_number,
                "verification_code": captcha_code
            }
            search_resp = session.get(CMS_BASE_URL, params=params, verify=False, timeout=REQUEST_TIMEOUT)
            search_resp.raise_for_status()
            
            search_soup = BeautifulSoup(search_resp.text, "html.parser")
            rows = search_soup.select("table tbody tr")
            
            # If we returned 0 rows, it means the captcha was CORRECT (it filtered), but the consent number doesn't exist
            if len(rows) == 0:
                logger.info(f"[{consent_number}] Query filtered successfully, but returned 0 rows. Consent number does not exist on CMS.")
                return None, None
                
            # If we returned 22 rows, the captcha was WRONG (it did not filter)
            if len(rows) == 22:
                logger.warning(f"Attempt {attempt} did not filter (possibly wrong captcha '{captcha_code}').")
                time.sleep(1.0)
                continue
                
            # Look for exact matching consent row
            for row in rows:
                cells = [td.get_text(" ", strip=True) for td in row.select("td")]
                if len(cells) >= 8:
                    row_consent = cells[1].strip()
                    if row_consent == consent_number:
                        link = row.select_one("a[href='#send_otp_modal']")
                        data_link = link.get("data-link", "") if link else ""
                        
                        metadata = {
                            "consent_number": row_consent,
                            "consent_type": cells[2].strip(),
                            "application_date": cells[3].strip(),
                            "issue_date": cells[4].strip(),
                            "industry_name": cells[5].strip(),
                            "address": cells[6].strip(),
                            "regional_office": cells[7].strip(),
                        }
                        logger.info(f"Found consent {consent_number} live on attempt {attempt}!")
                        return data_link, metadata
                        
            # If rows are returned but not 22, and we didn't find our exact consent, captcha was correct but no match
            logger.info(f"[{consent_number}] Query returned {len(rows)} rows, but none matched '{consent_number}'. Consent not found.")
            return None, None
            
        except Exception as e:
            logger.error(f"Error on attempt {attempt}: {e}")
            time.sleep(1.0)
            
    logger.error(f"Failed to retrieve consent {consent_number} live after {max_total_attempts} attempts.")
    return None, None

def resolve_blockchain_pdf_link(doc_url):
    """
    Resolve a blockchain doc page URL to a direct PDF download link.
    """
    session = get_session()
    try:
        resp = session.get(doc_url, verify=False, timeout=30)
        resp.raise_for_status()
        
        # Search for fileid in paragraph tags
        file_match = re.search(r'id="fileid"[^>]*>([^<]+)<', resp.text)
        user_match = re.search(r'id="aissuer"[^>]*>([^<]+)<', resp.text)
        
        if file_match:
            file_id = file_match.group(1).strip()
            user = user_match.group(1).strip() if user_match else ""
            pdf_url = f"https://blockchain.ecmpcb.in/file?id={file_id}&user={user}"
            return pdf_url
        else:
            # Fallback regex search for any direct download href
            match_href = re.search(r'href="(/file\?id=[^"]+)"', resp.text)
            if match_href:
                return f"https://blockchain.ecmpcb.in{match_href.group(1)}"
                
        logger.error(f"Could not extract file ID from blockchain doc page: {doc_url}")
        return None
    except Exception as e:
        logger.error(f"Failed to resolve blockchain PDF URL: {e}")
        return None

def download_pdf(pdf_url, output_path):
    """
    Download PDF file to local disk.
    """
    session = get_session()
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        resp = session.get(pdf_url, verify=False, timeout=45)
        resp.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(resp.content)
            
        logger.info(f"Downloaded PDF successfully to: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download PDF from {pdf_url}: {e}")
        return False
