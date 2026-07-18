import re
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Tuple, Dict, Any, Optional
from playwright.async_api import async_playwright
from logger import logger
from models import InspectionRecord
from config import BROWSER_CONFIG, PORTAL_URL, DATE_RANGE_MONTHS

def generate_date_chunks(months: int = 6) -> List[Tuple[str, str]]:
    """
    Generates 7-day date chunks for the past N months in DD-MM-YYYY format.
    """
    chunks = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    curr = start_date
    while curr < end_date:
        # Move forward 7 days at a time
        next_curr = min(curr + timedelta(days=7), end_date)
        chunks.append((curr.strftime("%d-%m-%Y"), next_curr.strftime("%d-%m-%Y")))
        curr = next_curr
        
    logger.info(f"Generated {len(chunks)} date chunks for scraping.")
    return chunks

def parse_date(date_str: str) -> date:
    """Parses date string of format 'January 5, 2026' or similar into date object."""
    date_str_clean = date_str.strip()
    # Try MMMM D, YYYY format
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str_clean, fmt).date()
        except ValueError:
            continue
    # Fallback to today if parsing fails
    logger.warning(f"Could not parse date string '{date_str}', falling back to today.")
    return datetime.today().date()

def extract_region(inspector_text: str) -> Optional[str]:
    """Extracts office/region abbreviation inside parentheses, e.g. FO-Tarapur I -> Tarapur I."""
    match = re.search(r'\(([^)]+)\)', inspector_text)
    if match:
        content = match.group(1)
        # Strip prefixes like FO-, SRO-, RO- if present (ordered by longest prefix first)
        content_clean = re.sub(r'^(?:FO\s*-\s*|SRO\s*-\s*|RO\s*-\s*|FO|SRO|RO)\s*', '', content, flags=re.IGNORECASE)
        # Clean up leading hyphens and spaces
        return content_clean.strip().lstrip("-").strip()
    return None

def extract_officer_name(inspector_text: str) -> str:
    """Strips region parentheses to get the name of the officer."""
    name = re.sub(r'\(.*\)', '', inspector_text)
    return name.strip()

def extract_district(address_text: str) -> Optional[str]:
    """Extracts district name from address using regex."""
    if not address_text:
        return None
    match = re.search(r'Dist(?:rict)?\s*:?\s*([A-Za-z]+)', address_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_midc(address_text: str) -> Optional[str]:
    """Extracts MIDC area name from address using regex."""
    if not address_text:
        return None
    # Matches 'MIDC Tarapur' or 'Tarapur MIDC'
    match = re.search(r'MIDC\s+([A-Za-z0-9\-]+)|([A-Za-z0-9\-]+)\s+MIDC', address_text, re.IGNORECASE)
    if match:
        val = match.group(1) or match.group(2)
        return val.strip() if val else None
    return None

async def scrape_chunk_with_retry(page, chunk_start: str, chunk_end: str, attempt: int = 1) -> List[InspectionRecord]:
    """
    Attempts to navigate and scrape a single date chunk, with 3 retries on timeout or failure.
    """
    url = f"{PORTAL_URL}?from_date={chunk_start}&to_date={chunk_end}&unit_name=&records=ALL"
    timeout = BROWSER_CONFIG.get("timeout_ms", 60000)
    
    logger.info(f"Navigating to chunk range: {chunk_start} to {chunk_end} (Attempt {attempt}/3)")
    try:
        await page.goto(url, timeout=timeout)
        # Wait a short duration to ensure JavaScript tables render completely
        await page.wait_for_timeout(3000)
        
        # Check if the table exists
        table = await page.query_selector("table")
        if not table:
            logger.warning(f"No table element found for chunk {chunk_start} to {chunk_end}.")
            return []
            
        # Parse table headers
        headers = await table.query_selector_all("thead th")
        header_names = []
        for h in headers:
            text = (await h.inner_text()).strip()
            header_names.append(text)
            
        logger.info(f"Detected table headers: {header_names}")
        
        # Normalize and map headers dynamically to expected columns
        # Index map from original column to standard meanings
        col_map = {}
        for idx, h_name in enumerate(header_names):
            norm_name = re.sub(r'[^a-z0-9_]', '', h_name.lower().replace(" ", "_"))
            col_map[norm_name] = idx
            
        # We parse tbody rows using page.evaluate to fetch all text at once (avoiding massive Playwright RPC loop overhead)
        js_code = """
        () => {
            const rows = Array.from(document.querySelectorAll("table tbody tr"));
            return rows.map(row => {
                const tds = Array.from(row.querySelectorAll("td"));
                return tds.map(td => td.innerText.trim());
            });
        }
        """
        rows_data = await page.evaluate(js_code)
        records: List[InspectionRecord] = []
        
        current_date: Optional[date] = None
        
        for td_texts in rows_data:
            if not td_texts:
                continue
                
            # Handle rowspan for the date column:
            if len(td_texts) == 7:
                date_str = td_texts[1]
                current_date = parse_date(date_str)
                
                factory_name = td_texts[2]
                address = td_texts[3]
                dept_text = td_texts[4]
                inspector_text = td_texts[5]
                contact_details = td_texts[6]
            elif len(td_texts) == 6:
                # Omitted date, use active rowspan date
                if current_date is None:
                    logger.warning("Found row without date but current_date is None. Defaulting to today.")
                    current_date = datetime.today().date()
                    
                factory_name = td_texts[1]
                address = td_texts[2]
                dept_text = td_texts[3]
                inspector_text = td_texts[4]
                contact_details = td_texts[5]
            else:
                # Skip irregular rows
                continue
                
            # Parse inspection type & department from dept_text (e.g. MPCB\nHigh Risk)
            dept_lines = [line.strip() for line in dept_text.split('\n') if line.strip()]
            inspection_dept = dept_lines[0] if len(dept_lines) > 0 else "MPCB"
            inspection_type = dept_lines[1] if len(dept_lines) > 1 else "Standard"
            
            # Extract inspector name and office/region
            officer_name = extract_officer_name(inspector_text)
            region = extract_region(inspector_text)
            
            # Extract district and MIDC from the address
            district = extract_district(address)
            midc = extract_midc(address)
            
            record = InspectionRecord(
                factory_name=factory_name,
                inspection_date=current_date,
                inspection_type=inspection_type,
                region=region,
                district=district,
                midc=midc,
                officer_name=officer_name,
                status="Scheduled",
                remarks=None,
                address=address,
                inspection_dept=inspection_dept,
                contact_details=contact_details,
                source_url=url
            )
            records.append(record)
            
        logger.info(f"Successfully scraped {len(records)} records from chunk {chunk_start} to {chunk_end}.")
        return records
        
    except Exception as e:
        logger.warning(f"Error scraping chunk {chunk_start} to {chunk_end} on attempt {attempt}: {e}")
        if attempt < 3:
            await asyncio.sleep(3)
            return await scrape_chunk_with_retry(page, chunk_start, chunk_end, attempt + 1)
        else:
            logger.error(f"Failed to scrape chunk {chunk_start} to {chunk_end} after 3 attempts.")
            raise e

async def run_scraper_pipeline() -> Tuple[List[InspectionRecord], int, List[str]]:
    """
    Coordinates browser automation to scrape the last 6 months chunk-by-chunk.
    Returns:
        A tuple of (all_scraped_records, total_chunks_scraped, error_messages_list).
    """
    chunks = generate_date_chunks(DATE_RANGE_MONTHS)
    all_records: List[InspectionRecord] = []
    chunks_scraped = 0
    errors: List[str] = []
    
    headless = BROWSER_CONFIG.get("headless", True)
    
    async with async_playwright() as p:
        logger.info(f"Launching Playwright browser (headless={headless})...")
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        
        for chunk_start, chunk_end in chunks:
            try:
                records = await scrape_chunk_with_retry(page, chunk_start, chunk_end)
                all_records.extend(records)
                chunks_scraped += 1
            except Exception as e:
                err_msg = f"Failed to scrape range {chunk_start} to {chunk_end}: {e}"
                errors.append(err_msg)
                logger.error(err_msg)
                # Keep scraping other chunks
                continue
                
        await browser.close()
        
    logger.info(f"Pipeline finished. Total records scraped: {len(all_records)}. Successful chunks: {chunks_scraped}/{len(chunks)}")
    return all_records, chunks_scraped, errors
